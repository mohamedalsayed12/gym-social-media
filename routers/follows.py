from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import oauth2
import schemas
from database import get_db

router = APIRouter(tags=["follows"])


def _ensure_user_exists(user_id: int, db: Session) -> None:
    if db.query(models.User.id).filter(models.User.id == user_id).first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"user with id: {user_id} was not found",
        )


@router.post("/users/{id}/follow", status_code=status.HTTP_201_CREATED)
def follow_user(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    if id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot follow yourself",
        )
    _ensure_user_exists(id, db)

    db.add(models.Follow(follower_id=current_user.id, followed_id=id))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You already follow user {id}",
        ) from exc
    return {"message": f"now following user {id}"}


@router.delete("/users/{id}/follow", status_code=status.HTTP_204_NO_CONTENT)
def unfollow_user(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    deleted = (
        db.query(models.Follow)
        .filter(
            models.Follow.follower_id == current_user.id,
            models.Follow.followed_id == id,
        )
        .delete(synchronize_session=False)
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"You do not follow user {id}",
        )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/users/{id}/follow-stats", response_model=schemas.FollowStats)
def follow_stats(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _ensure_user_exists(id, db)
    followers = db.query(func.count()).filter(models.Follow.followed_id == id).scalar()
    following = db.query(func.count()).filter(models.Follow.follower_id == id).scalar()
    return {"user_id": id, "followers": followers, "following": following}


@router.get("/feed", response_model=list[schemas.PostOut])
def feed(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    limit: int = Query(default=10, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
):
    """Published posts from the people the current user follows, newest first."""
    followed_ids = (
        db.query(models.Follow.followed_id)
        .filter(models.Follow.follower_id == current_user.id)
        .scalar_subquery()
    )
    return (
        db.query(models.Post, func.count(models.Vote.post_id).label("votes"))
        .join(models.Vote, models.Vote.post_id == models.Post.id, isouter=True)
        .filter(models.Post.owner_id.in_(followed_ids), models.Post.published.is_(True))
        .group_by(models.Post.id)
        .order_by(models.Post.created_at.desc(), models.Post.id.desc())
        .limit(limit)
        .offset(skip)
        .all()
    )
