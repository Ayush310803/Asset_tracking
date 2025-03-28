from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
from sqlalchemy.sql import func
from database import Base
from app.models.assets_model import Asset

class AssetLocation(Base):
    __tablename__ = "asset_locations"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey('assets.id'), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    location = Column(Geometry(geometry_type='POINT', srid=4326))
    additional_data = Column(JSONB)

    asset = relationship("Asset", back_populates="locations")