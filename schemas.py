from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, conint, field_validator
from typing import Optional


class PostBase(BaseModel):
    title: str
    content: str
    published: bool = True


class PostCreate(PostBase):
    pass

class UserOut(BaseModel):
    id: int
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)


class Post(PostBase):
    id:int
    created_at: datetime
    owner_id:int | None
    owner:UserOut | None
    model_config = ConfigDict(from_attributes=True)


class PostWithVotes(BaseModel):
    post: Post
    votes: int


class PostOut(BaseModel):
    Post: Post
    votes: int
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email:EmailStr
    password:str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: Optional[str]=None


class Vote(BaseModel):
    post_id: int
    dir: conint(ge=0, le=1)


class ExerciseIn(BaseModel):
    exercise: str = Field(min_length=1, max_length=80)
    sets: int = Field(gt=0, le=100)
    reps: int = Field(gt=0, le=1000)
    weight_kg: Decimal = Field(ge=0, le=1000, max_digits=6, decimal_places=2)

    @field_validator("exercise")
    @classmethod
    def normalise_exercise(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("exercise name cannot be blank")
        return cleaned.title()


class ExerciseOut(ExerciseIn):
    id: int
    model_config = ConfigDict(from_attributes=True)


class WorkoutCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    performed_on: date
    notes: Optional[str] = Field(default=None, max_length=1000)
    exercises: list[ExerciseIn] = Field(min_length=1, max_length=50)


class WorkoutOut(BaseModel):
    id: int
    owner_id: int
    title: str
    performed_on: date
    notes: Optional[str]
    created_at: datetime
    exercises: list[ExerciseOut]
    model_config = ConfigDict(from_attributes=True)


class PersonalRecord(BaseModel):
    exercise: str
    weight_kg: Decimal
    reps: int
    performed_on: date
    workout_id: int


class FollowStats(BaseModel):
    user_id: int
    followers: int
    following: int
