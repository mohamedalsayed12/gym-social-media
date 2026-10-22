from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    muscle_group: Mapped[str] = mapped_column(String(40))

    workout_exercises: Mapped[list["WorkoutExercise"]] = relationship(back_populates="exercise")
