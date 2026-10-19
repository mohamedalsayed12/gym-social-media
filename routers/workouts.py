from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

import models
import oauth2
import schemas
from database import get_db

router = APIRouter(prefix="/workouts", tags=["workouts"])


def _get_owned_workout(workout_id: int, db: Session, user: models.User) -> models.Workout:
    workout = (
        db.query(models.Workout)
        .options(selectinload(models.Workout.exercises))
        .filter(models.Workout.id == workout_id)
        .first()
    )
    if workout is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"workout with id: {workout_id} was not found",
        )
    if workout.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform requested action",
        )
    return workout


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.WorkoutOut)
def create_workout(
    workout: schemas.WorkoutCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    new_workout = models.Workout(
        owner_id=current_user.id,
        title=workout.title,
        performed_on=workout.performed_on,
        notes=workout.notes,
        exercises=[models.WorkoutExercise(**item.model_dump()) for item in workout.exercises],
    )
    db.add(new_workout)
    db.commit()
    db.refresh(new_workout)
    return new_workout


@router.get("/", response_model=list[schemas.WorkoutOut])
def list_workouts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    limit: int = Query(default=10, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
):
    return (
        db.query(models.Workout)
        .options(selectinload(models.Workout.exercises))
        .filter(models.Workout.owner_id == current_user.id)
        .order_by(models.Workout.performed_on.desc(), models.Workout.id.desc())
        .limit(limit)
        .offset(skip)
        .all()
    )


@router.get("/records", response_model=list[schemas.PersonalRecord])
def personal_records(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    """Heaviest set per exercise. Ties go to more reps, then the earliest date."""
    ranked = (
        select(
            models.WorkoutExercise.exercise,
            models.WorkoutExercise.weight_kg,
            models.WorkoutExercise.reps,
            models.Workout.performed_on,
            models.Workout.id.label("workout_id"),
            func.row_number()
            .over(
                partition_by=models.WorkoutExercise.exercise,
                order_by=(
                    models.WorkoutExercise.weight_kg.desc(),
                    models.WorkoutExercise.reps.desc(),
                    models.Workout.performed_on.asc(),
                ),
            )
            .label("rank"),
        )
        .join(models.Workout, models.Workout.id == models.WorkoutExercise.workout_id)
        .where(models.Workout.owner_id == current_user.id)
        .subquery()
    )
    rows = db.execute(
        select(ranked).where(ranked.c.rank == 1).order_by(ranked.c.exercise)
    ).mappings()
    return [schemas.PersonalRecord(**row) for row in rows]


@router.get("/{id}", response_model=schemas.WorkoutOut)
def get_workout(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    return _get_owned_workout(id, db, current_user)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    workout = _get_owned_workout(id, db, current_user)
    db.delete(workout)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
