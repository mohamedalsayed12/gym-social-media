from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Workout(Base):
    __tablename__ = "workouts"
    __table_args__ = (
        CheckConstraint(
            "visibility IN ('public', 'followers', 'private')",
            name="ck_workouts_visibility",
        ),
        Index("ix_workouts_owner_performed", "owner_id", "performed_at"),
        Index("ix_workouts_visibility_performed", "visibility", "performed_at", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    visibility: Mapped[str] = mapped_column(String(16), server_default="public")
    photo_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped["User"] = relationship(back_populates="workouts")
    exercises: Mapped[list["WorkoutExercise"]] = relationship(
        back_populates="workout",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="WorkoutExercise.position",
    )


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    workout_id: Mapped[int] = mapped_column(ForeignKey("workouts.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column()

    workout: Mapped["Workout"] = relationship(back_populates="exercises")
    exercise: Mapped["Exercise"] = relationship(back_populates="workout_exercises")
    sets: Mapped[list["Set"]] = relationship(
        back_populates="workout_exercise",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Set.set_number",
    )


class Set(Base):
    __tablename__ = "sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    workout_exercise_id: Mapped[int] = mapped_column(
        ForeignKey("workout_exercises.id", ondelete="CASCADE"), index=True
    )
    set_number: Mapped[int] = mapped_column()
    reps: Mapped[int] = mapped_column()
    weight: Mapped[float] = mapped_column(Float)
    e1rm: Mapped[float] = mapped_column(Float, server_default=text("0"))
    is_pr: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))

    workout_exercise: Mapped["WorkoutExercise"] = relationship(back_populates="sets")


class Like(Base):
    __tablename__ = "likes"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    workout_id: Mapped[int] = mapped_column(
        ForeignKey("workouts.id", ondelete="CASCADE"), primary_key=True, index=True
    )
