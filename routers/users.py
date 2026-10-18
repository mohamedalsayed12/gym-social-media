from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import models
import oauth2
import schemas
import utils
from database import get_db

router = APIRouter(prefix="/users",
                   tags=["users"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model= schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User.id).filter(models.User.email == user.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )
    ##password hashing
    new_user = models.User(email=user.email, password=utils.hash(user.password))
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if getattr(exc.orig, "pgcode", None) == "23505":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            ) from exc
        raise
    db.refresh(new_user)

    return new_user



@router.get("/{id}", response_model=schemas.UserOut)
def get_user(id: int, current_user: models.User = Depends(oauth2.get_current_user)):
    if id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user",
        )

    return current_user
