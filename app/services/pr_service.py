from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.exercise import Exercise
from app.models.user import User
from app.models.workout import Set, Workout, WorkoutExercise


def is_personal_record(weight: float, previous_best: float | None) -> bool:
    if previous_best is None:
        return True
    return weight > previous_best


def personal_record_indexes(weights: list[float], previous_best: float | None) -> list[int]:
    """Indexes whose weight beats every earlier best, including earlier sets in this list."""
    best = previous_best
    indexes: list[int] = []
    for index, weight in enumerate(weights):
        if is_personal_record(weight, best):
            indexes.append(index)
            best = weight
    return indexes


def previous_best_weight(
    db: Session,
    owner_id: int,
    exercise_id: int,
    before: datetime,
    exclude_workout_id: int | None = None,
) -> float | None:
    statement = (
        select(func.max(Set.weight))
        .join(WorkoutExercise, Set.workout_exercise_id == WorkoutExercise.id)
        .join(Workout, WorkoutExercise.workout_id == Workout.id)
        .where(
            Workout.owner_id == owner_id,
            WorkoutExercise.exercise_id == exercise_id,
            Workout.performed_at < before,
        )
    )
    if exclude_workout_id is not None:
        statement = statement.where(Workout.id != exclude_workout_id)
    return db.scalar(statement)


def relative_score(lift: float, bodyweight_kg: float, height_cm: float) -> float:
    """Lift per kilogram of bodyweight, scaled by height in metres.

    A lighter lifter outranks a heavier one who lifts the same bar.
    A taller lifter outranks a shorter one at the same bodyweight, because the bar travels farther.
    """
    return lift / bodyweight_kg * (height_cm / 100)


def public_scores(db: Session) -> dict[str, dict[int, float]]:
    """Relative-strength score of each lifter's heaviest public set, by exercise."""
    rows = db.execute(
        select(Exercise.name, Workout.owner_id, func.max(Set.weight), User.bodyweight_kg, User.height_cm)
        .select_from(Set)
        .join(WorkoutExercise, Set.workout_exercise_id == WorkoutExercise.id)
        .join(Workout, WorkoutExercise.workout_id == Workout.id)
        .join(Exercise, WorkoutExercise.exercise_id == Exercise.id)
        .join(User, Workout.owner_id == User.id)
        .where(
            Workout.visibility == "public",
            User.bodyweight_kg.is_not(None),
            User.height_cm.is_not(None),
        )
        .group_by(Exercise.name, Workout.owner_id, User.bodyweight_kg, User.height_cm)
    ).all()
    boards: dict[str, dict[int, float]] = {}
    for name, owner_id, weight, bodyweight_kg, height_cm in rows:
        boards.setdefault(name, {})[owner_id] = relative_score(
            float(weight), float(bodyweight_kg), float(height_cm)
        )
    return boards


def boards_for(boards: dict[str, dict[int, float]], user_ids: set[int]) -> dict[str, dict[int, float]]:
    """Keep only the lifters who belong to one community."""
    scoped: dict[str, dict[int, float]] = {}
    for name, board in boards.items():
        kept = {user_id: score for user_id, score in board.items() if user_id in user_ids}
        if kept:
            scoped[name] = kept
    return scoped


def lift_standing(weight: float, owner_id: int, board: dict[int, float]) -> tuple[int, int, int]:
    """Rank, field size, and percentile against other lifters on this exercise.

    Percentile is the share of other lifters this weight matches or beats.
    A lifter with no one to compare against is in the 100th percentile.
    """
    others = [best for user_id, best in board.items() if user_id != owner_id]
    heavier = sum(best > weight for best in others)
    matched_or_beaten = sum(best <= weight for best in others)
    percentile = 100 if not others else round(100 * matched_or_beaten / len(others))
    return heavier + 1, len(others) + 1, percentile


def overall_standing(
    owner_id: int,
    records: list[tuple[str, float]],
    boards: dict[str, dict[int, float]],
) -> tuple[int | None, int, int | None]:
    """Overall rank, field size, and percentile from the mean of each lift's percentile."""
    if not records:
        return None, 0, None
    own = [lift_standing(weight, owner_id, boards.get(name, {}))[2] for name, weight in records]
    score = round(sum(own) / len(own))
    scores: dict[int, int] = {}
    public_users = {user_id for board in boards.values() for user_id in board}
    for user_id in public_users:
        parts = [
            lift_standing(board[user_id], user_id, board)[2]
            for name, board in boards.items()
            if user_id in board
        ]
        if parts:
            scores[user_id] = round(sum(parts) / len(parts))
    scores[owner_id] = score
    heavier = sum(other > score for user_id, other in scores.items() if user_id != owner_id)
    return heavier + 1, len(scores), score


def pr_flags(db: Session, workout: Workout) -> dict[int, bool]:
    flags: dict[int, bool] = {}
    for block in workout.exercises:
        previous = previous_best_weight(
            db,
            workout.owner_id,
            block.exercise_id,
            workout.performed_at,
            exclude_workout_id=workout.id,
        )
        ordered = sorted(block.sets, key=lambda item: item.set_number)
        indexes = set(personal_record_indexes([item.weight for item in ordered], previous))
        for index, item in enumerate(ordered):
            flags[item.id] = index in indexes
    return flags
