from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return password_hasher.verify(plain_password, hashed_password)
    except (ValueError, TypeError):
        return False


def _encode(user_id: int, token_type: str, minutes: int) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=minutes)
    payload = {"sub": str(user_id), "type": token_type, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(user_id: int) -> str:
    return _encode(user_id, "access", settings.access_token_expire_minutes)


def create_refresh_token(user_id: int) -> str:
    return _encode(user_id, "refresh", settings.refresh_token_expire_minutes)


def decode_token(token: str, expected_type: str) -> int:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except JWTError as exc:
        raise credentials_exception from exc

    if payload.get("type") != expected_type:
        raise credentials_exception
    subject = payload.get("sub")
    if subject is None:
        raise credentials_exception
    try:
        return int(subject)
    except (TypeError, ValueError) as exc:
        raise credentials_exception from exc


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    user_id = decode_token(token, "access")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
