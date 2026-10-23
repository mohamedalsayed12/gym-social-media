from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.workout import FeedPage, MuscleGroupIn
from app.services import feed_service

router = APIRouter(prefix="/feed", tags=["Feed"])


@router.get("/", response_model=FeedPage)
def get_feed(
    exercise: str | None = Query(default=None, max_length=80),
    muscle_group: MuscleGroupIn | None = None,
    performed_from: datetime | None = None,
    performed_to: datetime | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
    scope: str = Query(default="discover", pattern="^(discover|following|mine)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return feed_service.list_feed(
            db,
            current_user,
            exercise=exercise,
            muscle_group=muscle_group,
            performed_from=performed_from,
            performed_to=performed_to,
            limit=limit,
            cursor=cursor,
            scope=scope,
        )
    except feed_service.InvalidCursor as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
