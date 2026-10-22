from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.community import CommunityCreate, CommunityOut
from app.services import community_service

router = APIRouter(prefix="/communities", tags=["Communities"])


def _one(db: Session, user: User, slug: str) -> CommunityOut:
    match = next((item for item in community_service.list_communities(db, user) if item.slug == slug), None)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")
    return match


@router.get("/", response_model=list[CommunityOut])
def list_communities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return community_service.list_communities(db, current_user)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=CommunityOut)
def create_community(
    body: CommunityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        community = community_service.create_community(db, current_user, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _one(db, current_user, community.slug)


@router.post("/{slug}/join", response_model=CommunityOut)
def join_community(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    community = community_service.get_community(db, slug)
    if community is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")
    try:
        community_service.join_community(db, current_user, community)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _one(db, current_user, slug)


@router.delete("/{slug}/join", status_code=status.HTTP_204_NO_CONTENT)
def leave_community(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    community = community_service.get_community(db, slug)
    if community is None or not community_service.leave_community(db, current_user, community):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
