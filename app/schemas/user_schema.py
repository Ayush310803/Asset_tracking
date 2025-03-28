from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from enum import Enum

class Role(str, Enum):
    admin = "admin"
    user = "user"

class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: Role = Role.user

class UserCreate(UserBase):
    password: str
    admin_secret_code: Optional[str] = Field(None, min_length=1)

class UserInDB(UserBase):
    id: int
    disabled: bool
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None