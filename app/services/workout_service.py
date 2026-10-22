import uuid
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.exercise import Exercise
from app.models.user import User
from app.models.workout import Like, Set, Workout, WorkoutExercise
from app.schemas.workout import ExerciseIn, WorkoutCreate, WorkoutUpdate
from app.services.feed_service import _LOAD

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
MAX_PHOTO_BYTES = 5 * 1024 * 1024


def get_or_create_exercise(db: Session, name: str, muscle_group: str) -> Exercise:
    cleaned = name.strip()
    existing = db.scalar(select(Exercise).where(func.lower(Exercise.name) == cleaned.lower()))
    if existing is not None:
        return existing
    exercise = Exercise(name=cleaned, muscle_group=muscle_group.strip())
    db.add(exercise)
    db.flush()
    return exercise


def _replace_exercises(db: Session, workout: Workout, exercises: list[ExerciseIn]) -> None:
    workout.exercises.clear()
    db.flush()
    for position, block in enumerate(exercises):
        exercise = get_or_create_exercise(db, block.name, block.muscle_group)
        link = WorkoutExercise(exercise=exercise, position=position)
        for number, item in enumerate(block.sets, start=1):
            link.sets.append(Set(set_number=number, reps=item.reps, weight=item.weight))
        workout.exercises.append(link)


def get_workout(db: Session, workout_id: int) -> Workout | None:
    return db.scalar(select(Workout).where(Workout.id == workout_id).options(*_LOAD))


def create_workout(db: Session, owner: User, data: WorkoutCreate) -> Workout:
    workout = Workout(
        owner_id=owner.id,
        notes=data.notes,
        performed_at=data.performed_at,
        visibility=data.visibility,
    )
    db.add(workout)
    _replace_exercises(db, workout, data.exercises)
    db.commit()
    loaded = get_workout(db, workout.id)
    if loaded is None:
        raise RuntimeError("Workout disappeared after insert")
    return loaded


def update_workout(db: Session, workout: Workout, data: WorkoutUpdate) -> Workout:
    changes = data.model_dump(exclude_unset=True)
    exercises = changes.pop("exercises", None)
    for field, value in changes.items():
        setattr(workout, field, value)
    if exercises is not None:
        if len(exercises) == 0:
            raise ValueError("A workout needs at least one exercise")
        _replace_exercises(db, workout, data.exercises or [])
    db.commit()
    loaded = get_workout(db, workout.id)
    if loaded is None:
        raise RuntimeError("Workout disappeared after update")
    return loaded


def delete_workout(db: Session, workout: Workout) -> None:
    photo = workout.photo_name
    db.delete(workout)
    db.commit()
    _remove_photo(photo)


def _image_extension(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    return None


def _remove_photo(photo_name: str | None) -> None:
    if not photo_name:
        return
    path = UPLOAD_DIR / photo_name
    if path.is_file():
        path.unlink()


def save_photo(db: Session, workout: Workout, data: bytes) -> None:
    if len(data) > MAX_PHOTO_BYTES:
        raise ValueError("Photo must be under 5 MB")
    extension = _image_extension(data)
    if extension is None:
        raise ValueError("Use a JPEG, PNG, or WebP photo")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{extension}"
    (UPLOAD_DIR / filename).write_bytes(data)
    previous = workout.photo_name
    workout.photo_name = filename
    db.commit()
    _remove_photo(previous)


def like_workout(db: Session, user: User, workout: Workout) -> bool:
    existing = db.scalar(select(Like).where(Like.user_id == user.id, Like.workout_id == workout.id))
    if existing is not None:
        return False
    db.add(Like(user_id=user.id, workout_id=workout.id))
    db.commit()
    return True


def unlike_workout(db: Session, user: User, workout: Workout) -> bool:
    existing = db.scalar(select(Like).where(Like.user_id == user.id, Like.workout_id == workout.id))
    if existing is None:
        return False
    db.delete(existing)
    db.commit()
    return True
