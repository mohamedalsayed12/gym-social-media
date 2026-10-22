from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.community import Community, Membership
from app.models.exercise import Exercise
from app.models.user import User
from app.models.workout import Set, Workout, WorkoutExercise
from app.schemas.community import CommunityCreate, CommunityOut
from app.services.pr_service import boards_for, overall_standing, public_scores, relative_score

DEFAULTS = (
    ("bodybuilding", "Bodybuilding", "Hypertrophy, physique, and stage prep."),
    ("pilates", "Pilates", "Control, core, and mobility."),
    ("powerlifting", "Powerlifting", "Squat, bench, and deadlift."),
)


def slugify(name: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in name.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")[:40]


def ensure_defaults(db: Session) -> None:
    existing = set(db.scalars(select(Community.slug)).all())
    missing = [item for item in DEFAULTS if item[0] not in existing]
    if not missing:
        return
    for slug, name, description in missing:
        db.add(Community(slug=slug, name=name, description=description))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()


def _best_scores(db: Session, user: User) -> list[tuple[str, float]]:
    if user.bodyweight_kg is None or user.height_cm is None:
        return []
    rows = db.execute(
        select(Exercise.name, func.max(Set.weight))
        .select_from(Set)
        .join(WorkoutExercise, Set.workout_exercise_id == WorkoutExercise.id)
        .join(Workout, WorkoutExercise.workout_id == Workout.id)
        .join(Exercise, WorkoutExercise.exercise_id == Exercise.id)
        .where(Workout.owner_id == user.id)
        .group_by(Exercise.name)
    ).all()
    return [
        (name, relative_score(float(weight), user.bodyweight_kg, user.height_cm)) for name, weight in rows
    ]


def list_communities(db: Session, user: User) -> list[CommunityOut]:
    ensure_defaults(db)
    communities = db.scalars(select(Community).order_by(Community.name)).all()
    counts = dict(
        db.execute(select(Membership.community_id, func.count()).group_by(Membership.community_id)).all()
    )
    joined = set(db.scalars(select(Membership.community_id).where(Membership.user_id == user.id)).all())
    members: dict[int, set[int]] = {}
    for community_id, user_id in db.execute(select(Membership.community_id, Membership.user_id)).all():
        members.setdefault(community_id, set()).add(user_id)
    scores = _best_scores(db, user)
    boards = public_scores(db) if scores else {}
    listed: list[CommunityOut] = []
    for community in communities:
        rank = lifters = percentile = None
        if community.id in joined and scores:
            standing = overall_standing(user.id, scores, boards_for(boards, members.get(community.id, set())))
            rank, lifters, percentile = standing
        listed.append(
            CommunityOut(
                slug=community.slug,
                name=community.name,
                description=community.description,
                members=int(counts.get(community.id, 0)),
                joined=community.id in joined,
                rank=rank,
                ranked_lifters=lifters or 0,
                percentile=percentile,
            )
        )
    return listed


def create_community(db: Session, user: User, data: CommunityCreate) -> Community:
    slug = slugify(data.name)
    if len(slug) < 2:
        raise ValueError("Use a community name with letters or numbers")
    if db.scalar(select(Community.id).where(Community.slug == slug)) is not None:
        raise ValueError("That community already exists")
    community = Community(slug=slug, name=data.name.strip(), description=data.description.strip())
    db.add(community)
    db.flush()
    db.add(Membership(user_id=user.id, community_id=community.id))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("That community already exists") from exc
    db.refresh(community)
    return community


def get_community(db: Session, slug: str) -> Community | None:
    ensure_defaults(db)
    return db.scalar(select(Community).where(Community.slug == slug))


def join_community(db: Session, user: User, community: Community) -> None:
    existing = db.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.community_id == community.id,
        )
    )
    if existing is not None:
        raise ValueError("Already in this community")
    db.add(Membership(user_id=user.id, community_id=community.id))
    db.commit()


def leave_community(db: Session, user: User, community: Community) -> bool:
    row = db.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.community_id == community.id,
        )
    )
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True
