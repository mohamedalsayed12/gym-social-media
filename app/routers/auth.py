from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.db.database import get_db
from app.schemas.user import RefreshRequest, Token
from app.services import user_service

router = APIRouter(tags=["Authentication"])


def _token_pair(user_id: int) -> Token:
    return Token(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.post("/login", response_model=Token)
def login(
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = user_service.find_login_user(db, user_credentials.username)
    if user is None or not verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")
    return _token_pair(user.id)


@router.post("/refresh", response_model=Token)
def refresh(body: RefreshRequest):
    user_id = decode_token(body.refresh_token, "refresh")
    return _token_pair(user_id)
