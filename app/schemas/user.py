from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None

class User(UserBase):
    id: int
    date_inscription: datetime
    is_admin: bool

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str
