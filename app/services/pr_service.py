"""Personal records and strength rankings.

PR flags are written to the sets table when a workout is saved, so reading a feed never has to
replay anyone's history. Rankings use estimated one-rep maxes per kilogram of bodyweight and are
computed in Postgres with window functions, so the work stays in the database as the user count grows.
"""

from collections import defaultdict
from itertools import groupby

from sqlalchemy import Integer, Numeric, case, cast, func, literal, or_, select, update
from sqlalchemy.orm import Session

from app.models.community import Membership
from app.models.user import User
from app.models.workout import Set, Workout, WorkoutExercise

Standing = tuple[int, int, int]  # rank, lifters on the board, percentile


def estimated_one_rep_max(weight: float, reps: int) -> float:
    """Epley formula. A single is already a true max, so it is returned unchanged."""
    if reps <= 1:
        return weight
    return weight * (1 + reps / 30)


def relative_score(e1rm: float, bodyweight_kg: float) -> float:
    return e1rm / bodyweight_kg


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


def recompute_prs(db: Session, owner_id: int, exercise_ids: set[int]) -> None:
    """Rewrite is_pr for one lifter's history on the given exercises.

    Adding, editing or deleting a workout can change whether later sets were records, so the
    whole history for each touched exercise is replayed. That is one indexed query per save,
    instead of one query per exercise per workout every time a feed is read.
    """
    if not exercise_ids:
        return
    rows = db.execute(
        select(
            WorkoutExercise.exercise_id,
            Workout.performed_at,
            WorkoutExercise.id,
            Set.id,
            Set.weight,
            Set.is_pr,
        )
        .join(WorkoutExercise, Set.workout_exercise_id == WorkoutExercise.id)
        .join(Workout, WorkoutExercise.workout_id == Workout.id)
        .where(Workout.owner_id == owner_id, WorkoutExercise.exercise_id.in_(exercise_ids))
        .order_by(
            WorkoutExercise.exercise_id,
            Workout.performed_at,
            Workout.id,
            WorkoutExercise.position,
            Set.set_number,
        )
    ).all()

    became_pr: list[int] = []
    lost_pr: list[int] = []
    for _, history in groupby(rows, key=lambda row: row[0]):
        best_before: float | None = None
        # Workouts logged at the same moment don't count against each other.
        for _, same_time in groupby(history, key=lambda row: row[1]):
            same_time = list(same_time)
            for _, block in groupby(same_time, key=lambda row: row[2]):
                block = list(block)
                winners = set(personal_record_indexes([row[4] for row in block], best_before))
                for index, row in enumerate(block):
                    flag = index in winners
                    if flag != row[5]:
                        (became_pr if flag else lost_pr).append(row[3])
            heaviest = max(row[4] for row in same_time)
            best_before = heaviest if best_before is None else max(best_before, heaviest)

    if became_pr:
        db.execute(update(Set).where(Set.id.in_(became_pr)).values(is_pr=True))
    if lost_pr:
        db.execute(update(Set).where(Set.id.in_(lost_pr)).values(is_pr=False))


def _best_scores(viewer_id: int, exercise_ids: list[int] | None = None):
    """Each lifter's best e1RM per exercise, divided by bodyweight.

    Other lifters only count their public workouts. The viewer always sees their own lifts,
    including private ones, ranked against that public board.
    """
    best = (
        select(
            Workout.owner_id.label("user_id"),
            WorkoutExercise.exercise_id.label("exercise_id"),
            func.max(Set.e1rm).label("best"),
        )
        .join(WorkoutExercise, Set.workout_exercise_id == WorkoutExercise.id)
        .join(Workout, WorkoutExercise.workout_id == Workout.id)
        .where(or_(Workout.visibility == "public", Workout.owner_id == viewer_id))
        .group_by(Workout.owner_id, WorkoutExercise.exercise_id)
    )
    if exercise_ids is not None:
        best = best.where(WorkoutExercise.exercise_id.in_(exercise_ids))
    best = best.subquery()
    return (
        select(
            best.c.user_id,
            best.c.exercise_id,
            (best.c.best / User.bodyweight_kg).label("score"),
        )
        .join(User, User.id == best.c.user_id)
        .where(User.bodyweight_kg.is_not(None), User.bodyweight_kg > 0)
    )


def _per_lift(scores, scope):
    """Rank and percentile on each exercise board. Percentile is the share of the other lifters
    you match or beat; a lifter alone on a board is in the 100th percentile."""
    board = (scope, scores.c.exercise_id)
    field = func.count().over(partition_by=board)
    matched_or_beaten = func.count().over(partition_by=board, order_by=scores.c.score, range_=(None, 0))
    percentile = case(
        (field == 1, 100),
        else_=cast(func.round(cast(100.0 * (matched_or_beaten - 1) / (field - 1), Numeric)), Integer),
    )
    return select(
        scope.label("scope"),
        scores.c.user_id,
        scores.c.exercise_id,
        func.rank().over(partition_by=board, order_by=scores.c.score.desc()).label("rank"),
        field.label("lifters"),
        percentile.label("percentile"),
    )


def lift_standings(db: Session, viewer_id: int, exercise_ids: list[int]) -> dict[int, Standing]:
    """The viewer's standing on each exercise across every lifter."""
    if not exercise_ids:
        return {}
    scores = _best_scores(viewer_id, exercise_ids).subquery()
    lifts = _per_lift(scores, literal(0)).subquery()
    rows = db.execute(
        select(lifts.c.exercise_id, lifts.c.rank, lifts.c.lifters, lifts.c.percentile).where(
            lifts.c.user_id == viewer_id
        )
    ).all()
    return {exercise_id: (rank, lifters, percentile) for exercise_id, rank, lifters, percentile in rows}


def overall_standings(
    db: Session, viewer_id: int, community_ids: list[int] | None = None
) -> dict[int, Standing]:
    """Overall standing from the mean of each lift's percentile.

    With no community ids this ranks against every lifter and the result is keyed by 0.
    Otherwise each community is ranked separately against its own members only.
    """
    if community_ids == []:
        return {}
    scores = _best_scores(viewer_id)
    if community_ids is None:
        scores = scores.subquery()
        scope = literal(0)
    else:
        scores = (
            scores.add_columns(Membership.community_id)
            .join(Membership, Membership.user_id == User.id)
            .where(Membership.community_id.in_(community_ids))
            .subquery()
        )
        scope = scores.c.community_id

    lifts = _per_lift(scores, scope).subquery()
    per_lifter = (
        select(
            lifts.c.scope,
            lifts.c.user_id,
            cast(func.round(func.avg(lifts.c.percentile)), Integer).label("percentile"),
        )
        .group_by(lifts.c.scope, lifts.c.user_id)
        .subquery()
    )
    ranked = select(
        per_lifter.c.scope,
        per_lifter.c.user_id,
        func.rank()
        .over(partition_by=per_lifter.c.scope, order_by=per_lifter.c.percentile.desc())
        .label("rank"),
        func.count().over(partition_by=per_lifter.c.scope).label("lifters"),
        per_lifter.c.percentile,
    ).subquery()
    rows = db.execute(
        select(ranked.c.scope, ranked.c.rank, ranked.c.lifters, ranked.c.percentile).where(
            ranked.c.user_id == viewer_id
        )
    ).all()
    standings: dict[int, Standing] = defaultdict(lambda: (None, 0, None))
    for scope_id, rank, lifters, percentile in rows:
        standings[scope_id] = (rank, lifters, percentile)
    return standings
