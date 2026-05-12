import logging
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/register", response_model=schemas.User, status_code=201)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.user.get_by_email(db, email=user_in.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if crud.user.get_by_username(db, username=user_in.username):
        raise HTTPException(status_code=400, detail="Username already taken")

    verification_token = secrets.token_urlsafe(32)
    user = crud.user.create(db, obj_in=user_in, verification_token=verification_token)

    # Email skip : on log le lien (visible dans la console uvicorn)
    confirm_url = f"{settings.FRONTEND_URL}/confirm-email?token={verification_token}"
    logger.warning("[EMAIL-SKIPPED] Confirmation pour %s : %s", user.email, confirm_url)

    return user


@router.post("/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = crud.user.get_by_identifier(db, identifier=credentials.username)
    if not user or not security.verify_password(credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive account")

    access_token = security.create_access_token(subject=user.username)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.User)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/confirm-email", response_model=schemas.User)
def confirm_email(token: str, db: Session = Depends(get_db)):
    user = crud.user.get_by_verification_token(db, token=token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    return crud.user.mark_verified(db, user=user)


@router.post("/forgot-password", status_code=202)
def forgot_password(payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = crud.user.get_by_email(db, email=payload.email)
    # Toujours répondre 202 pour ne pas révéler l'existence du compte
    if user:
        token = secrets.token_urlsafe(32)
        user.password_reset_token = token
        user.password_reset_expires_at = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        logger.warning("[EMAIL-SKIPPED] Reset password pour %s : %s", user.email, reset_url)
    return {"detail": "If the email exists, a reset link has been sent."}


@router.post("/reset-password", response_model=schemas.User)
def reset_password(payload: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    user = crud.user.get_by_reset_token(db, token=payload.token)
    if not user or not user.password_reset_expires_at:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    if user.password_reset_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expired")
    return crud.user.set_password(db, user=user, new_password=payload.new_password)

