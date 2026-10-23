from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.user import Token


def _invalid() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def issue_tokens(db: Session, user_id: int) -> Token:
    refresh_token, jti, expires_at = create_refresh_token(user_id)
    db.add(RefreshToken(jti=jti, user_id=user_id, expires_at=expires_at))
    db.commit()
    return Token(access_token=create_access_token(user_id), refresh_token=refresh_token)


def rotate(db: Session, refresh_token: str) -> Token:
    """Swap a refresh token for a new pair. Each refresh token works once.

    If a token that was already used turns up again, someone else has a copy of it, so every
    session for that user is revoked and they have to sign in again.
    """
    payload = decode_token(refresh_token, "refresh")
    row = db.scalar(select(RefreshToken).where(RefreshToken.jti == payload.get("jti")).with_for_update())
    if row is None or row.user_id != payload["sub"]:
        raise _invalid()
    if row.revoked_at is not None:
        revoke_all(db, row.user_id)
        raise _invalid()
    if db.get(User, row.user_id) is None:
        raise _invalid()
    row.revoked_at = datetime.now(UTC)
    return issue_tokens(db, row.user_id)


def revoke(db: Session, refresh_token: str) -> None:
    try:
        payload = decode_token(refresh_token, "refresh")
    except HTTPException:
        return  # Expired or malformed tokens can't be used anyway.
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.jti == payload.get("jti"), RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    db.commit()


def revoke_all(db: Session, user_id: int) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    db.commit()
