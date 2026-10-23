from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.models.workout import Workout
from app.schemas.workout import WorkoutCreate, WorkoutOut, WorkoutUpdate
from app.services import feed_service, workout_service

router = APIRouter(prefix="/workouts", tags=["Workouts"])


def require_owned_workout(detail: str):
    def dependency(
        workout_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> Workout:
        workout = workout_service.get_workout(db, workout_id)
        if workout is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
        if workout.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
        return workout

    return dependency


def _visible_workout(db: Session, workout_id: int, viewer: User) -> Workout:
    workout = workout_service.get_workout(db, workout_id)
    if workout is None or not feed_service.can_view(db, workout, viewer):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    return workout


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=WorkoutOut)
def create_workout(
    body: WorkoutCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workout = workout_service.create_workout(db, current_user, body)
    return feed_service.serialize_workout(db, workout, current_user.id)


@router.get("/{workout_id}", response_model=WorkoutOut)
def get_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workout = _visible_workout(db, workout_id, current_user)
    return feed_service.serialize_workout(db, workout, current_user.id)


@router.patch("/{workout_id}", response_model=WorkoutOut)
def update_workout(
    body: WorkoutUpdate,
    workout: Workout = Depends(require_owned_workout("You can only edit your own workouts")),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        updated = workout_service.update_workout(db, workout, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return feed_service.serialize_workout(db, updated, current_user.id)


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(
    workout: Workout = Depends(require_owned_workout("You can only delete your own workouts")),
    db: Session = Depends(get_db),
):
    workout_service.delete_workout(db, workout)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{workout_id}/photo", response_model=WorkoutOut)
async def add_photo(
    file: UploadFile,
    workout: Workout = Depends(require_owned_workout("You can only edit your own workouts")),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        data = await workout_service.read_upload(file)
    except workout_service.PhotoTooLarge as exc:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)) from exc
    try:
        workout_service.save_photo(db, workout, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    refreshed = workout_service.get_workout(db, workout.id)
    return feed_service.serialize_workout(db, refreshed, current_user.id)


@router.post("/{workout_id}/like", response_model=WorkoutOut)
def like_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workout = _visible_workout(db, workout_id, current_user)
    if not workout_service.like_workout(db, current_user, workout):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already liked this workout")
    refreshed = workout_service.get_workout(db, workout.id)
    return feed_service.serialize_workout(db, refreshed, current_user.id)


@router.delete("/{workout_id}/like", response_model=WorkoutOut)
def unlike_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workout = _visible_workout(db, workout_id, current_user)
    if not workout_service.unlike_workout(db, current_user, workout):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Like does not exist")
    refreshed = workout_service.get_workout(db, workout.id)
    return feed_service.serialize_workout(db, refreshed, current_user.id)
