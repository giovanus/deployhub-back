from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import crud, schemas
from app.core import security
from app.core.database import get_db

router = APIRouter()

@router.post("/register", response_model=schemas.user.User)
def register(user_in: schemas.user.UserCreate, db: Session = Depends(get_db)):
    user = crud.user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    user = crud.user.get_by_username(db, username=user_in.username)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    return crud.user.create(db, obj_in=user_in)

@router.post("/login", response_model=schemas.token.Token)
def login(user_credentials: schemas.user.UserLogin, db: Session = Depends(get_db)):
    user = crud.user.get_by_username(db, username=user_credentials.username)
    if not user or not security.verify_password(user_credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = security.create_access_token(subject=user.username)
    return {"access_token": access_token, "token_type": "bearer"}
