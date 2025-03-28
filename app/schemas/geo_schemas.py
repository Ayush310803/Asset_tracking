from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class GeoZoneBase(BaseModel):
    name: str
    coordinates: List[List[float]]  

class GeoZoneCreate(GeoZoneBase):
    asset_id: int

class GeoZoneResponse(GeoZoneBase):
    id: int
    asset_id: int
    created_at: datetime
    class Config:
        from_attributes = True

class GeoAlertResponse(BaseModel):
    id: int
    asset_id: int
    alert_type: str
    message: str
    latitude: float
    longitude: float
    triggered_at: datetime
    resolved: bool
    class Config:
        from_attributes = True