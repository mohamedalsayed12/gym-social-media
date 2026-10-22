from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.workout import WorkoutOut
from app.services import feed_service

router = APIRouter(prefix="/feed", tags=["Feed"])


@router.get("/", response_model=list[WorkoutOut])
def get_feed(
    exercise: str | None = None,
    muscle_group: str | None = None,
    performed_from: datetime | None = None,
    performed_to: datetime | None = None,
    limit: int = Query(default=10, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
    scope: str = Query(default="discover", pattern="^(discover|following|mine)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workouts = feed_service.list_feed(
        db,
        current_user,
        exercise=exercise,
        muscle_group=muscle_group,
        performed_from=performed_from,
        performed_to=performed_to,
        limit=limit,
        skip=skip,
        scope=scope,
    )
    return workouts
