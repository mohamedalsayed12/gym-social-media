from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field

Visibility = Literal["public", "followers", "private"]
MuscleGroup = Literal["chest", "back", "shoulders", "arms", "legs", "core", "full_body"]

# People type what they train, not a region, so common names are mapped onto the body-map regions.
MUSCLE_ALIASES = {
    "pec": "chest",
    "pecs": "chest",
    "lat": "back",
    "lats": "back",
    "traps": "back",
    "shoulder": "shoulders",
    "delt": "shoulders",
    "delts": "shoulders",
    "bicep": "arms",
    "biceps": "arms",
    "tricep": "arms",
    "triceps": "arms",
    "forearms": "arms",
    "quad": "legs",
    "quads": "legs",
    "hamstring": "legs",
    "hamstrings": "legs",
    "glute": "legs",
    "glutes": "legs",
    "calf": "legs",
    "calves": "legs",
    "ab": "core",
    "abs": "core",
    "abdominals": "core",
    "full body": "full_body",
    "general": "full_body",
}


def normalise_muscle_group(value: object) -> object:
    if not isinstance(value, str):
        return value
    key = value.strip().lower()
    return MUSCLE_ALIASES.get(key, key)


MuscleGroupIn = Annotated[MuscleGroup, BeforeValidator(normalise_muscle_group)]


class SetIn(BaseModel):
    reps: int = Field(ge=1, le=100)
    weight: float = Field(ge=0, le=1000)


class ExerciseIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    muscle_group: MuscleGroupIn
    sets: list[SetIn] = Field(min_length=1, max_length=100)


class WorkoutCreate(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)
    performed_at: datetime
    visibility: Visibility = "public"
    exercises: list[ExerciseIn] = Field(min_length=1, max_length=50)


class WorkoutUpdate(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)
    performed_at: datetime | None = None
    visibility: Visibility | None = None
    exercises: list[ExerciseIn] | None = Field(default=None, max_length=50)


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


class OwnerOut(BaseModel):
    id: int
    username: str


class WorkoutOut(BaseModel):
    id: int
    notes: str | None
    performed_at: datetime
    visibility: Visibility
    owner: OwnerOut
    exercises: list[ExerciseOut]
    likes: int
    liked_by_me: bool
    photo_url: str | None = None


class FeedPage(BaseModel):
    items: list[WorkoutOut]
    next_cursor: str | None = None
