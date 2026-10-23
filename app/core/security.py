import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")
password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return password_hasher.verify(plain_password, hashed_password)
    except (ValueError, TypeError):
        return False


def _unauthorized(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _encode(payload: dict, minutes: int) -> str:
    claims = {**payload, "exp": datetime.now(UTC) + timedelta(minutes=minutes)}
    return jwt.encode(claims, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(user_id: int) -> str:
    return _encode({"sub": str(user_id), "type": "access"}, settings.access_token_expire_minutes)


def create_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    """Return the token, its id, and when it expires. The caller stores the id."""
    jti = uuid.uuid4().hex
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.refresh_token_expire_minutes)
    token = _encode(
        {"sub": str(user_id), "type": "refresh", "jti": jti}, settings.refresh_token_expire_minutes
    )
    return token, jti, expires_at


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise _unauthorized() from exc

    if payload.get("type") != expected_type:
        raise _unauthorized()
    try:
        payload["sub"] = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise _unauthorized() from exc
    return payload


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    user_id = decode_token(token, "access")["sub"]
    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized()
    return user
