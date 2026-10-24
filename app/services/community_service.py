from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.community import Community, Membership
from app.models.user import User
from app.schemas.community import CommunityCreate, CommunityOut
from app.services.pr_service import overall_standings


def slugify(name: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in name.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")[:40]


def _to_out(db: Session, user: User, communities: list[Community]) -> list[CommunityOut]:
    ids = [community.id for community in communities]
    counts = dict(
        db.execute(
            select(Membership.community_id, func.count())
            .where(Membership.community_id.in_(ids))
            .group_by(Membership.community_id)
        ).all()
    )
    joined = set(
        db.scalars(
            select(Membership.community_id).where(
                Membership.user_id == user.id, Membership.community_id.in_(ids)
            )
        )
    )
    standings = overall_standings(db, user.id, sorted(joined))
    listed = []
    for community in communities:
        rank, lifters, percentile = standings.get(community.id, (None, 0, None))
        listed.append(
            CommunityOut(
                slug=community.slug,
                name=community.name,
                description=community.description,
                members=counts.get(community.id, 0),
                joined=community.id in joined,
                rank=rank,
                ranked_lifters=lifters,
                percentile=percentile,
            )
        )
    return listed


def list_communities(db: Session, user: User) -> list[CommunityOut]:
    communities = list(db.scalars(select(Community).order_by(Community.name)))
    return _to_out(db, user, communities)


def community_out(db: Session, user: User, community: Community) -> CommunityOut:
    return _to_out(db, user, [community])[0]


def create_community(db: Session, user: User, data: CommunityCreate) -> Community:
    slug = slugify(data.name)
    if len(slug) < 2:
        raise ValueError("Use a community name with letters or numbers")
    community = Community(slug=slug, name=data.name.strip(), description=data.description.strip())
    db.add(community)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("That community already exists") from exc
    db.add(Membership(user_id=user.id, community_id=community.id))
    db.commit()
    db.refresh(community)
    return community


def get_community(db: Session, slug: str) -> Community | None:
    return db.scalar(select(Community).where(Community.slug == slug))


def join_community(db: Session, user: User, community: Community) -> None:
    result = db.execute(
        insert(Membership).values(user_id=user.id, community_id=community.id).on_conflict_do_nothing()
    )
    db.commit()
    if result.rowcount == 0:
        raise ValueError("Already in this community")


def leave_community(db: Session, user: User, community: Community) -> bool:
    result = db.execute(
        delete(Membership).where(Membership.user_id == user.id, Membership.community_id == community.id)
    )
    db.commit()
    return result.rowcount == 1
