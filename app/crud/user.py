from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash

def get_by_username(db: Session, *, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def get_by_email(db: Session, *, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def create(db: Session, *, obj_in: UserCreate) -> User:
    db_obj = User(
        username=obj_in.username,
        email=obj_in.email,
        password=get_password_hash(obj_in.password),
        is_admin=False
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
