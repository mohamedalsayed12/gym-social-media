from pydantic import BaseModel, ConfigDict, EmailStr, conint
from datetime import datetime



class PostBase(BaseModel):
    title: str
    content: str
    published: bool = True



class PostCreate(PostBase):
    pass

class UserOut(BaseModel):
    id:int
    email:EmailStr

    class config:
        orm_mode=True


class Post(PostBase):
    id:int
    created_at: datetime
    owner_id:int | None
    owner:UserOut | None
    model_config = ConfigDict(from_attributes=True)

    class config:
        orm_mode=True


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


from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: Optional[str]=None


class Vote(BaseModel):
    post_id: int
    dir: conint(ge=0, le=1)

    




