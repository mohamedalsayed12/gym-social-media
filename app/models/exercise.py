from sqlalchemy import CheckConstraint, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

MUSCLE_GROUPS = ("chest", "back", "shoulders", "arms", "legs", "core", "full_body")


class Exercise(Base):
    """A catalogue exercise (owner_id is NULL) or a lifter's own custom one.

    Splitting them stops one user's typo or odd muscle group from changing everyone else's lift.
    """

    __tablename__ = "exercises"
    __table_args__ = (
        CheckConstraint(
            "muscle_group IN ('chest', 'back', 'shoulders', 'arms', 'legs', 'core', 'full_body')",
            name="ck_exercises_muscle_group",
        ),
        Index(
            "uq_exercises_catalogue_name",
            func.lower(text("name")),
            unique=True,
            postgresql_where=text("owner_id IS NULL"),
        ),
        Index(
            "uq_exercises_owner_name",
            "owner_id",
            func.lower(text("name")),
            unique=True,
            postgresql_where=text("owner_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    muscle_group: Mapped[str] = mapped_column(String(40))
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    workout_exercises: Mapped[list["WorkoutExercise"]] = relationship(back_populates="exercise")
