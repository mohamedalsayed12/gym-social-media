import logging
import uuid

from fastapi import UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.exercise import Exercise
from app.models.user import User
from app.models.workout import Like, Set, Workout, WorkoutExercise
from app.schemas.workout import ExerciseIn, WorkoutCreate, WorkoutUpdate
from app.services.feed_service import LOAD_WORKOUT
from app.services.pr_service import estimated_one_rep_max, recompute_prs
from app.services.storage import get_storage

logger = logging.getLogger(__name__)

READ_CHUNK = 64 * 1024


class PhotoTooLarge(ValueError):
    pass


def resolve_exercise(db: Session, owner_id: int, name: str, muscle_group: str) -> Exercise:
    """Use the lifter's own exercise if they have one, then the shared catalogue, else create
    a custom one for them. Catalogue entries keep their muscle group whatever the user typed."""
    cleaned = name.strip()
    lowered = cleaned.lower()
    own = db.scalar(
        select(Exercise).where(Exercise.owner_id == owner_id, func.lower(Exercise.name) == lowered)
    )
    if own is not None:
        own.muscle_group = muscle_group
        return own
    shared = db.scalar(
        select(Exercise).where(Exercise.owner_id.is_(None), func.lower(Exercise.name) == lowered)
    )
    if shared is not None:
        return shared
    db.execute(
        insert(Exercise)
        .values(name=cleaned, muscle_group=muscle_group, owner_id=owner_id)
        .on_conflict_do_nothing()
    )
    return db.scalar(
        select(Exercise).where(Exercise.owner_id == owner_id, func.lower(Exercise.name) == lowered)
    )


def _lock_owner(db: Session, owner_id: int) -> None:
    db.execute(select(User.id).where(User.id == owner_id).with_for_update())


def _replace_exercises(db: Session, workout: Workout, exercises: list[ExerciseIn]) -> set[int]:
    previous = {block.exercise_id for block in workout.exercises}
    workout.exercises.clear()
    db.flush()
    with db.no_autoflush:
        for position, block in enumerate(exercises):
            exercise = resolve_exercise(db, workout.owner_id, block.name, block.muscle_group)
            link = WorkoutExercise(exercise=exercise, position=position)
            for number, item in enumerate(block.sets, start=1):
                link.sets.append(
                    Set(
                        set_number=number,
                        reps=item.reps,
                        weight=item.weight,
                        e1rm=estimated_one_rep_max(item.weight, item.reps),
                    )
                )
            workout.exercises.append(link)
    db.flush()
    return previous | {block.exercise_id for block in workout.exercises}


def get_workout(db: Session, workout_id: int) -> Workout | None:
    return db.scalar(
        select(Workout)
        .where(Workout.id == workout_id)
        .options(*LOAD_WORKOUT)
        .execution_options(populate_existing=True)
    )


def create_workout(db: Session, owner: User, data: WorkoutCreate) -> Workout:
    _lock_owner(db, owner.id)
    workout = Workout(
        owner_id=owner.id,
        notes=data.notes,
        performed_at=data.performed_at,
        visibility=data.visibility,
    )
    db.add(workout)
    touched = _replace_exercises(db, workout, data.exercises)
    recompute_prs(db, owner.id, touched)
    db.commit()
    return get_workout(db, workout.id)


def update_workout(db: Session, workout: Workout, data: WorkoutUpdate) -> Workout:
    changes = data.model_dump(exclude_unset=True)
    exercises = changes.pop("exercises", None)
    if exercises is not None and len(exercises) == 0:
        raise ValueError("A workout needs at least one exercise")
    _lock_owner(db, workout.owner_id)
    for field, value in changes.items():
        setattr(workout, field, value)
    touched = {block.exercise_id for block in workout.exercises}
    if exercises is not None:
        touched |= _replace_exercises(db, workout, data.exercises)
    db.flush()
    if exercises is not None or "performed_at" in changes:
        recompute_prs(db, workout.owner_id, touched)
    db.commit()
    return get_workout(db, workout.id)


def delete_workout(db: Session, workout: Workout) -> None:
    photo = workout.photo_name
    owner_id = workout.owner_id
    touched = {block.exercise_id for block in workout.exercises}
    _lock_owner(db, owner_id)
    db.delete(workout)
    db.flush()
    recompute_prs(db, owner_id, touched)
    db.commit()
    _remove_photo(photo)


def _image_type(data: bytes) -> tuple[str, str] | None:
    """Sniff the real file type from its first bytes; the client's Content-Type can't be trusted."""
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp", "image/webp"
    return None


async def read_upload(file: UploadFile, limit: int = settings.max_photo_bytes) -> bytes:
    """Read at most `limit` bytes, stopping early so an oversized upload never sits fully in memory."""
    chunks: list[bytes] = []
    size = 0
    while chunk := await file.read(READ_CHUNK):
        size += len(chunk)
        if size > limit:
            raise PhotoTooLarge(f"Photo must be under {limit // (1024 * 1024)} MB")
        chunks.append(chunk)
    return b"".join(chunks)


def _remove_photo(photo_name: str | None) -> None:
    if not photo_name:
        return
    try:
        get_storage().delete(photo_name)
    except Exception:
        logger.exception("Could not delete photo %s", photo_name)


def save_photo(db: Session, workout: Workout, data: bytes) -> None:
    detected = _image_type(data)
    if detected is None:
        raise ValueError("Use a JPEG, PNG, or WebP photo")
    extension, content_type = detected
    filename = f"{uuid.uuid4().hex}{extension}"
    get_storage().save(filename, data, content_type)
    previous = workout.photo_name
    workout.photo_name = filename
    db.commit()
    _remove_photo(previous)


def like_workout(db: Session, user: User, workout: Workout) -> bool:
    """Return False if it was already liked. ON CONFLICT makes a double-tap safe instead of a 500."""
    result = db.execute(insert(Like).values(user_id=user.id, workout_id=workout.id).on_conflict_do_nothing())
    db.commit()
    return result.rowcount == 1


def unlike_workout(db: Session, user: User, workout: Workout) -> bool:
    result = db.execute(delete(Like).where(Like.user_id == user.id, Like.workout_id == workout.id))
    db.commit()
    return result.rowcount == 1
