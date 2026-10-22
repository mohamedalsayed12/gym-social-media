from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.exercise import Exercise
from app.models.follow import Follow
from app.models.user import User
from app.models.workout import Workout, WorkoutExercise
from app.schemas.workout import ExerciseOut, OwnerOut, SetOut, WorkoutOut
from app.services.pr_service import pr_flags


def photo_url(photo_name: str | None) -> str | None:
    if not photo_name:
        return None
    return f"/media/{photo_name}"


_LOAD = (
    selectinload(Workout.owner),
    selectinload(Workout.likes),
    selectinload(Workout.exercises).selectinload(WorkoutExercise.exercise),
    selectinload(Workout.exercises).selectinload(WorkoutExercise.sets),
)


def can_view(db: Session, workout: Workout, viewer: User) -> bool:
    if workout.owner_id == viewer.id:
        return True
    if workout.visibility == "public":
        return True
    if workout.visibility != "followers":
        return False
    follow = db.scalar(
        select(Follow).where(
            Follow.follower_id == viewer.id,
            Follow.following_id == workout.owner_id,
        )
    )
    return follow is not None


def to_workout_out(db: Session, workout: Workout, viewer_id: int) -> WorkoutOut:
    flags = pr_flags(db, workout)
    return WorkoutOut(
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
                        is_pr=flags.get(item.id, False),
                    )
                    for item in sorted(block.sets, key=lambda row: row.set_number)
                ],
            )
            for block in sorted(workout.exercises, key=lambda row: row.position)
        ],
        likes=len(workout.likes),
        liked_by_me=any(like.user_id == viewer_id for like in workout.likes),
        photo_url=photo_url(workout.photo_name),
    )


def list_feed(
    db: Session,
    viewer: User,
    *,
    exercise: str | None,
    muscle_group: str | None,
    performed_from: datetime | None,
    performed_to: datetime | None,
    limit: int,
    skip: int,
    scope: str = "discover",
) -> list[WorkoutOut]:
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
        statement = statement.join(Workout.exercises).join(WorkoutExercise.exercise)
        if exercise:
            statement = statement.where(Exercise.name.ilike(f"%{exercise}%"))
        if muscle_group:
            statement = statement.where(Exercise.muscle_group.ilike(f"%{muscle_group}%"))
    if performed_from is not None:
        statement = statement.where(Workout.performed_at >= performed_from)
    if performed_to is not None:
        statement = statement.where(Workout.performed_at <= performed_to)

    statement = (
        statement.options(*_LOAD)
        .distinct()
        .order_by(Workout.performed_at.desc(), Workout.id.desc())
        .limit(limit)
        .offset(skip)
    )
    workouts = db.scalars(statement).unique().all()
    return [to_workout_out(db, workout, viewer.id) for workout in workouts]
