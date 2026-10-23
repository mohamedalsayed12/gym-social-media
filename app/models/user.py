from datetime import datetime

from sqlalchemy import DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    password: Mapped[str] = mapped_column(String)
    bodyweight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workouts: Mapped[list["Workout"]] = relationship(back_populates="owner")
    following: Mapped[list["Follow"]] = relationship(
        back_populates="follower",
        foreign_keys="Follow.follower_id",
    )
    followers: Mapped[list["Follow"]] = relationship(
        back_populates="following",
        foreign_keys="Follow.following_id",
    )
