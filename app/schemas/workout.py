from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Visibility = Literal["public", "followers", "private"]


class SetIn(BaseModel):
    reps: int = Field(ge=1, le=100)
    weight: float = Field(ge=0)


class ExerciseIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    muscle_group: str = Field(min_length=1, max_length=40)
    sets: list[SetIn] = Field(min_length=1, max_length=100)


class WorkoutCreate(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)
    performed_at: datetime
    visibility: Visibility = "public"
    exercises: list[ExerciseIn] = Field(min_length=1)


class WorkoutUpdate(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)
    performed_at: datetime | None = None
    visibility: Visibility | None = None
    exercises: list[ExerciseIn] | None = None


class SetOut(BaseModel):
    id: int
    set_number: int
    reps: int
    weight: float
    is_pr: bool


class ExerciseOut(BaseModel):
    id: int
    name: str
    muscle_group: str
    sets: list[SetOut]


class WorkoutOut(BaseModel):
    id: int
    notes: str | None
    performed_at: datetime
    visibility: Visibility
    owner: "OwnerOut"
    exercises: list[ExerciseOut]
    likes: int
    liked_by_me: bool
    photo_url: str | None = None


class OwnerOut(BaseModel):
    id: int
    username: str


WorkoutOut.model_rebuild()
