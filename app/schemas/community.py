from pydantic import BaseModel, Field


class CommunityCreate(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    description: str = Field(default="", max_length=200)


class CommunityOut(BaseModel):
    slug: str
    name: str
    description: str
    members: int
    joined: bool
    rank: int | None = None
    ranked_lifters: int = 0
    percentile: int | None = None
