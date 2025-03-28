from sqlalchemy.orm import Session
from app.models.users_model import User
from app.schemas.user_schema import UserCreate, UserInDB
from app.auth import get_password_hash, ADMIN_SECRET_CODE, verify_password

def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, user: UserCreate):
    if user.role == "admin":
        if user.admin_secret_code != ADMIN_SECRET_CODE:
            raise ValueError("Invalid admin secret code")
    
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        password=hashed_password,
        role=user.role,
        disabled=False
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user or not verify_password(password, user.password):
        return False
    return user