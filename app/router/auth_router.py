from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from database import get_db
from app.schemas.user_schema import Token, UserCreate, UserInDB
from app.crud.user_crud import create_user, authenticate_user
from app.auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES,get_current_user,get_current_admin_user

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(),db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserInDB)
async def register_user(user: UserCreate,db: Session = Depends(get_db)):
    try:
        return create_user(db, user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail=str(e))