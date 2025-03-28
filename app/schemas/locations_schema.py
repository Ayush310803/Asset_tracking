from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class LocationBase(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    timestamp: Optional[datetime] = None
    additional_data: Optional[dict] = None

class LocationCreate(LocationBase):
    pass

class LocationResponse(LocationBase):
    id: int
    asset_id: int
    timestamp: datetime
    
    class Config:
        from_attributes = True