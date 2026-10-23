import base64
from datetime import datetime

from sqlalchemy import and_, exists, func, or_, select, tuple_
from sqlalchemy.orm import Session, selectinload

from app.models.exercise import Exercise
from app.models.follow import Follow
from app.models.user import User
from app.models.workout import Like, Workout, WorkoutExercise
from app.schemas.workout import ExerciseOut, FeedPage, OwnerOut, SetOut, WorkoutOut
from app.services.storage import get_storage

LOAD_WORKOUT = (
    selectinload(Workout.owner),
    selectinload(Workout.exercises).selectinload(WorkoutExercise.exercise),
    selectinload(Workout.exercises).selectinload(WorkoutExercise.sets),
)


class InvalidCursor(ValueError):
    pass


def encode_cursor(workout: Workout) -> str:
    raw = f"{workout.performed_at.isoformat()}|{workout.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        performed_at, workout_id = base64.urlsafe_b64decode(cursor.encode()).decode().rsplit("|", 1)
        return datetime.fromisoformat(performed_at), int(workout_id)
    except (ValueError, UnicodeDecodeError) as exc:
        raise InvalidCursor("Invalid cursor") from exc


def can_view(db: Session, workout: Workout, viewer: User) -> bool:
    if workout.owner_id == viewer.id or workout.visibility == "public":
        return True
    if workout.visibility != "followers":
        return False
    return db.get(Follow, (viewer.id, workout.owner_id)) is not None


def serialize_workouts(db: Session, workouts: list[Workout], viewer_id: int) -> list[WorkoutOut]:
    """Turn workouts into API responses with two extra queries in total, not two per workout."""
    if not workouts:
        return []
    ids = [workout.id for workout in workouts]
    like_counts = dict(
        db.execute(
            select(Like.workout_id, func.count()).where(Like.workout_id.in_(ids)).group_by(Like.workout_id)
        ).all()
    )
    liked = set(
        db.scalars(select(Like.workout_id).where(Like.user_id == viewer_id, Like.workout_id.in_(ids)))
    )
    storage = get_storage()
    return [
        WorkoutOut(
            id=workout.id,
            notes=workout.notes,
            performed_at=workout.performed_at,
            visibility=workout.visibility,
            owner=OwnerOut(id=workout.owner.id, username=workout.owner.username),
            exercises=[
                ExerciseOut(
                    id=block.exercise.id,
                    name=block.exercise.name,
                    muscle_group=block.exercise.muscle_group,
                    sets=[
                        SetOut(
                            id=item.id,
                            set_number=item.set_number,
                            reps=item.reps,
                            weight=item.weight,
                            is_pr=item.is_pr,
                        )
                        for item in block.sets
                    ],
                )
                for block in workout.exercises
            ],
            likes=like_counts.get(workout.id, 0),
            liked_by_me=workout.id in liked,
            photo_url=storage.url(workout.photo_name) if workout.photo_name else None,
        )
        for workout in workouts
    ]


def serialize_workout(db: Session, workout: Workout, viewer_id: int) -> WorkoutOut:
    return serialize_workouts(db, [workout], viewer_id)[0]


def list_feed(
    db: Session,
    viewer: User,
    *,
    exercise: str | None,
    muscle_group: str | None,
    performed_from: datetime | None,
    performed_to: datetime | None,
    limit: int,
    cursor: str | None,
    scope: str = "discover",
) -> FeedPage:
    followed = select(Follow.following_id).where(Follow.follower_id == viewer.id)
    if scope == "mine":
        visible = Workout.owner_id == viewer.id
    elif scope == "following":
        visible = and_(
            Workout.owner_id.in_(followed),
            Workout.visibility.in_(("public", "followers")),
        )
    else:
        visible = or_(
            Workout.owner_id == viewer.id,
            Workout.visibility == "public",
            and_(Workout.visibility == "followers", Workout.owner_id.in_(followed)),
        )
    statement = select(Workout).where(visible)

    if exercise or muscle_group:
        # EXISTS rather than a JOIN, so a workout with two matching exercises isn't returned twice
        # and the query doesn't need DISTINCT, which would stop Postgres using the sort index.
        matches = (
            select(WorkoutExercise.id)
            .join(Exercise, WorkoutExercise.exercise_id == Exercise.id)
            .where(WorkoutExercise.workout_id == Workout.id)
        )
        if exercise:
            matches = matches.where(Exercise.name.ilike(f"%{_escape_like(exercise)}%", escape="\\"))
        if muscle_group:
            matches = matches.where(Exercise.muscle_group == muscle_group)
        statement = statement.where(exists(matches))
    if performed_from is not None:
        statement = statement.where(Workout.performed_at >= performed_from)
    if performed_to is not None:
        statement = statement.where(Workout.performed_at <= performed_to)
    if cursor is not None:
        # Keyset pagination: "older than the last row I saw". Unlike OFFSET, new posts arriving
        # don't shift the pages, and deep pages cost the same as the first one.
        after_time, after_id = decode_cursor(cursor)
        statement = statement.where(tuple_(Workout.performed_at, Workout.id) < (after_time, after_id))

    statement = (
        statement.options(*LOAD_WORKOUT)
        .order_by(Workout.performed_at.desc(), Workout.id.desc())
        .limit(limit + 1)
    )
    workouts = list(db.scalars(statement).all())
    has_more = len(workouts) > limit
    workouts = workouts[:limit]
    return FeedPage(
        items=serialize_workouts(db, workouts, viewer.id),
        next_cursor=encode_cursor(workouts[-1]) if has_more else None,
    )


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
