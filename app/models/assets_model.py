from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from app.models.users_model import User

class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    asset_type = Column(String, nullable=False)  
    unique_id = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="active") 
    user_id = Column(Integer, ForeignKey('users.id'))
    
    user = relationship('User', back_populates="assets")
    locations = relationship("AssetLocation", back_populates="asset", order_by="desc(AssetLocation.timestamp)")