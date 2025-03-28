from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Index
from geoalchemy2 import Geometry
from sqlalchemy.sql import func
from database import Base

class GeoZone(Base):
    __tablename__ = "geo_zones"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey('assets.id'), nullable=False)
    name = Column(String)
    zone = Column(Geometry(geometry_type='POLYGON', srid=4326))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_geo_zone', 'zone', postgresql_using='gist'),  
    )

class GeoAlert(Base):
    __tablename__ = "geo_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey('assets.id'), nullable=False)
    alert_type = Column(String) 
    message = Column(String)
    triggered_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved = Column(Boolean, default=False)