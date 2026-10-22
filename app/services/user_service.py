from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.follow import Follow
from app.models.user import User
from app.models.workout import Workout
from app.schemas.user import MuscleHit, MuscleVolume, ProfileOut, RecordOut, UserCreate
from app.services.feed_service import _LOAD, to_workout_out
from app.services.pr_service import lift_standing, overall_standing, public_scores, relative_score


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


def follow_user(db: Session, follower: User, target: User) -> Follow:
    row = Follow(follower_id=follower.id, following_id=target.id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def unfollow_user(db: Session, follower: User, target: User) -> bool:
    row = db.scalar(
        select(Follow).where(
            Follow.follower_id == follower.id,
            Follow.following_id == target.id,
        )
    )
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


MUSCLE_REGIONS = {
    "pec": "chest",
    "pecs": "chest",
    "lat": "back",
    "lats": "back",
    "traps": "back",
    "shoulder": "shoulders",
    "delts": "shoulders",
    "delt": "shoulders",
    "biceps": "arms",
    "triceps": "arms",
    "bis": "arms",
    "tris": "arms",
    "quads": "legs",
    "quad": "legs",
    "hamstrings": "legs",
    "hamstring": "legs",
    "glutes": "legs",
    "glute": "legs",
    "calves": "legs",
    "calf": "legs",
    "abs": "core",
    "abdominals": "core",
    "ab": "core",
}


def muscle_region(name: str) -> str:
    key = name.strip().lower()
    return MUSCLE_REGIONS.get(key, key)


def hit_percentages(counts: dict[str, int]) -> list[MuscleHit]:
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


def profile_snapshot(db: Session, user: User) -> ProfileOut:
    now = datetime.now(UTC)
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    workouts = db.scalar(select(func.count()).select_from(Workout).where(Workout.owner_id == user.id)) or 0
    following = db.scalar(select(func.count()).select_from(Follow).where(Follow.follower_id == user.id)) or 0
    rows = (
        db.scalars(
            select(Workout)
            .where(Workout.owner_id == user.id)
            .options(*_LOAD)
            .order_by(Workout.performed_at.desc())
            .limit(200)
        )
        .unique()
        .all()
    )
    cards = [to_workout_out(db, workout, user.id) for workout in rows]
    prs_this_month = 0
    week_volume: dict[str, float] = {}
    week_hits: dict[str, int] = {}
    records: dict[str, RecordOut] = {}
    for card in cards:
        seen_this_workout: set[str] = set()
        for exercise in card.exercises:
            region = muscle_region(exercise.muscle_group)
            for item in exercise.sets:
                if card.performed_at >= month_start and item.is_pr:
                    prs_this_month += 1
                if card.performed_at >= week_start:
                    week_volume[region] = week_volume.get(region, 0) + (item.reps * item.weight)
            if card.performed_at >= week_start and region not in seen_this_workout and exercise.sets:
                seen_this_workout.add(region)
                week_hits[region] = week_hits.get(region, 0) + 1
            current = records.get(exercise.name)
            for item in exercise.sets:
                if current is None or item.weight > current.weight:
                    current = RecordOut(name=exercise.name, weight=item.weight, reps=item.reps)
                    records[exercise.name] = current
    week = [
        MuscleVolume(muscle_group=name, volume=volume)
        for name, volume in sorted(week_volume.items(), key=lambda pair: pair[1], reverse=True)
    ]
    boards = public_scores(db)
    measured = user.bodyweight_kg is not None and user.height_cm is not None
    ranked: list[RecordOut] = []
    scored: list[tuple[str, float]] = []
    for record in list(records.values())[:8]:
        if measured:
            score = relative_score(record.weight, user.bodyweight_kg, user.height_cm)
            rank, lifters, percentile = lift_standing(score, user.id, boards.get(record.name, {}))
            scored.append((record.name, score))
        else:
            rank, lifters, percentile = 0, 0, 0
        ranked.append(record.model_copy(update={"rank": rank, "lifters": lifters, "percentile": percentile}))
    if measured:
        overall_rank, ranked_lifters, percentile = overall_standing(user.id, scored, boards)
    else:
        overall_rank, ranked_lifters, percentile = None, 0, None
    return ProfileOut(
        username=user.username,
        email=user.email,
        workouts=int(workouts),
        prs_this_month=prs_this_month,
        following=int(following),
        week=week,
        hits=hit_percentages(week_hits),
        records=ranked,
        rank=overall_rank,
        ranked_lifters=ranked_lifters,
        percentile=percentile,
        bodyweight_kg=user.bodyweight_kg,
        height_cm=user.height_cm,
    )


def is_following(db: Session, follower_id: int, target_id: int) -> bool:
    return (
        db.scalar(
            select(Follow).where(
                Follow.follower_id == follower_id,
                Follow.following_id == target_id,
            )
        )
        is not None
    )
