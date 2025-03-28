from sqlalchemy import Column, Integer, String, Enum, Boolean
from sqlalchemy.orm import relationship
from database import Base
import enum

class Role(enum.Enum):
    admin = "admin"
    user = "user"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(Enum(Role), default=Role.user)
    disabled = Column(Boolean, default=False)
    
    assets = relationship("Asset", back_populates="user")