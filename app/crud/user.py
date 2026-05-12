from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash


def get(db: Session, *, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_by_username(db: Session, *, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_by_email(db: Session, *, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_by_identifier(db: Session, *, identifier: str) -> Optional[User]:
    """Cherche par username OU email."""
    return (
        db.query(User)
        .filter((User.username == identifier) | (User.email == identifier))
        .first()
    )


def get_by_verification_token(db: Session, *, token: str) -> Optional[User]:
    return db.query(User).filter(User.email_verification_token == token).first()


def get_by_reset_token(db: Session, *, token: str) -> Optional[User]:
    return db.query(User).filter(User.password_reset_token == token).first()


def create(db: Session, *, obj_in: UserCreate, verification_token: Optional[str] = None) -> User:
    db_obj = User(
        username=obj_in.username,
        email=obj_in.email,
        password=get_password_hash(obj_in.password),
        is_admin=False,
        is_active=True,
        is_verified=False,
        email_verification_token=verification_token,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def set_password(db: Session, *, user: User, new_password: str) -> User:
    user.password = get_password_hash(new_password)
    user.password_reset_token = None
    user.password_reset_expires_at = None
    db.commit()
    db.refresh(user)
    return user


def mark_verified(db: Session, *, user: User) -> User:
    user.is_verified = True
    user.email_verification_token = None
    db.commit()
    db.refresh(user)
    return user

