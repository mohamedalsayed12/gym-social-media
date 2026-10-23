from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import verify_password
from app.db.database import get_db
from app.schemas.user import RefreshRequest, Token
from app.services import auth_service, user_service

router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=Token)
@limiter.limit(settings.login_rate_limit)
def login(
    request: Request,
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = user_service.find_login_user(db, user_credentials.username)
    if user is None or not verify_password(user_credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_service.issue_tokens(db, user.id)


@router.post("/refresh", response_model=Token)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    return auth_service.rotate(db, body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: RefreshRequest, db: Session = Depends(get_db)):
    auth_service.revoke(db, body.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
