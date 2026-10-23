from datetime import datetime, timedelta, tzinfo

from sqlalchemy import delete, distinct, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.exercise import Exercise
from app.models.follow import Follow
from app.models.user import User
from app.models.workout import Set, Workout, WorkoutExercise
from app.schemas.user import MuscleHit, MuscleVolume, ProfileOut, RecordOut, UserCreate, UserUpdate
from app.services.pr_service import lift_standings, overall_standings

RECORDS_SHOWN = 8


def create_user(db: Session, data: UserCreate, password_hash: str) -> User:
    user = User(
        email=data.email.lower(),
        username=data.username,
        password=password_hash,
        bodyweight_kg=data.bodyweight_kg,
        height_cm=data.height_cm,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, data: UserUpdate) -> User:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def find_login_user(db: Session, username_or_email: str) -> User | None:
    return db.scalar(
        select(User).where((User.email == username_or_email.lower()) | (User.username == username_or_email))
    )


def email_taken(db: Session, email: str) -> bool:
    return db.scalar(select(User.id).where(User.email == email.lower())) is not None


def username_taken(db: Session, username: str) -> bool:
    return db.scalar(select(User.id).where(User.username == username)) is not None


def follow_user(db: Session, follower: User, target: User) -> bool:
    """Return False if already following."""
    result = db.execute(
        insert(Follow).values(follower_id=follower.id, following_id=target.id).on_conflict_do_nothing()
    )
    db.commit()
    return result.rowcount == 1


def unfollow_user(db: Session, follower: User, target: User) -> bool:
    result = db.execute(
        delete(Follow).where(Follow.follower_id == follower.id, Follow.following_id == target.id)
    )
    db.commit()
    return result.rowcount == 1


def hit_percentages(counts: dict[str, int]) -> list[MuscleHit]:
    """Share of sessions per muscle group, rounded so the parts always add up to 100."""
    total = sum(counts.values())
    if total == 0:
        return []
    raw = {name: hits * 100 / total for name, hits in counts.items()}
    floors = {name: int(value) for name, value in raw.items()}
    leftover = 100 - sum(floors.values())
    for name in sorted(raw, key=lambda item: raw[item] - floors[item], reverse=True)[:leftover]:
        floors[name] += 1
    ordered = sorted(counts, key=lambda item: counts[item], reverse=True)
    return [MuscleHit(muscle_group=name, hits=counts[name], percent=floors[name]) for name in ordered]


def _own_sets(user_id: int):
    return (
        select(Set)
        .join(WorkoutExercise, Set.workout_exercise_id == WorkoutExercise.id)
        .join(Workout, WorkoutExercise.workout_id == Workout.id)
        .join(Exercise, WorkoutExercise.exercise_id == Exercise.id)
        .where(Workout.owner_id == user_id)
    )


def _best_records(db: Session, user_id: int) -> list[tuple[int, str, float, int]]:
    """Best set per exercise by e1RM, most recently trained exercises first."""
    ranked = (
        _own_sets(user_id)
        .with_only_columns(
            Exercise.id.label("exercise_id"),
            Exercise.name.label("name"),
            Set.weight.label("weight"),
            Set.reps.label("reps"),
            func.row_number()
            .over(partition_by=Exercise.id, order_by=(Set.e1rm.desc(), Set.weight.desc()))
            .label("position"),
            func.max(Workout.performed_at).over(partition_by=Exercise.id).label("last_trained"),
        )
        .subquery()
    )
    return db.execute(
        select(ranked.c.exercise_id, ranked.c.name, ranked.c.weight, ranked.c.reps)
        .where(ranked.c.position == 1)
        .order_by(ranked.c.last_trained.desc(), ranked.c.name)
        .limit(RECORDS_SHOWN)
    ).all()


def profile_snapshot(db: Session, user: User, now: datetime, zone: tzinfo) -> ProfileOut:
    """Everything on the profile screen, aggregated in SQL.

    Weeks and months start in the lifter's own time zone, so a Sunday-night session in London
    doesn't land in the wrong week.
    """
    local_now = now.astimezone(zone)
    week_start = (local_now - timedelta(days=local_now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    month_start = local_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    workouts = db.scalar(select(func.count()).select_from(Workout).where(Workout.owner_id == user.id))
    following = db.scalar(select(func.count()).select_from(Follow).where(Follow.follower_id == user.id))
    prs_this_month = db.scalar(
        _own_sets(user.id)
        .with_only_columns(func.count())
        .where(Set.is_pr.is_(True), Workout.performed_at >= month_start)
    )
    this_week = _own_sets(user.id).where(Workout.performed_at >= week_start)
    week = [
        MuscleVolume(muscle_group=muscle_group, volume=volume)
        for muscle_group, volume in db.execute(
            this_week.with_only_columns(
                Exercise.muscle_group, func.sum(Set.reps * Set.weight).label("volume")
            )
            .group_by(Exercise.muscle_group)
            .order_by(func.sum(Set.reps * Set.weight).desc())
        )
    ]
    hits = dict(
        db.execute(
            this_week.with_only_columns(Exercise.muscle_group, func.count(distinct(Workout.id))).group_by(
                Exercise.muscle_group
            )
        ).all()
    )

    best = _best_records(db, user.id)
    measured = user.bodyweight_kg is not None
    standings = lift_standings(db, user.id, [row.exercise_id for row in best]) if measured else {}
    records = []
    for exercise_id, name, weight, reps in best:
        rank, lifters, percentile = standings.get(exercise_id, (0, 0, 0))
        records.append(
            RecordOut(name=name, weight=weight, reps=reps, rank=rank, lifters=lifters, percentile=percentile)
        )
    overall_rank, ranked_lifters, percentile = (
        overall_standings(db, user.id)[0] if measured else (None, 0, None)
    )
    return ProfileOut(
        username=user.username,
        email=user.email,
        workouts=workouts or 0,
        prs_this_month=prs_this_month or 0,
        following=following or 0,
        week=week,
        hits=hit_percentages(hits),
        records=records,
        rank=overall_rank,
        ranked_lifters=ranked_lifters,
        percentile=percentile,
        bodyweight_kg=user.bodyweight_kg,
        height_cm=user.height_cm,
    )
