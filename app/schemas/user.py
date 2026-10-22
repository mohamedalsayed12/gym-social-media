from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(pattern=r"^[A-Za-z0-9_]{3,32}$")
    password: str = Field(min_length=8, max_length=128)
    bodyweight_kg: float = Field(ge=20, le=400)
    height_cm: float = Field(ge=50, le=250)


class UserPublic(BaseModel):
    id: int
    username: str
    model_config = ConfigDict(from_attributes=True)


class UserOut(UserPublic):
    email: EmailStr
    bodyweight_kg: float | None = None
    height_cm: float | None = None


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class MuscleVolume(BaseModel):
    muscle_group: str
    volume: float


class MuscleHit(BaseModel):
    muscle_group: str
    hits: int
    percent: int


class RecordOut(BaseModel):
    name: str
    weight: float
    reps: int
    rank: int = 0
    lifters: int = 0
    percentile: int = 0


class ProfileOut(BaseModel):
    username: str
    email: EmailStr
    workouts: int
    prs_this_month: int
    following: int
    week: list[MuscleVolume]
    hits: list[MuscleHit]
    records: list[RecordOut]
    rank: int | None = None
    ranked_lifters: int = 0
    percentile: int | None = None
    bodyweight_kg: float | None = None
    height_cm: float | None = None
