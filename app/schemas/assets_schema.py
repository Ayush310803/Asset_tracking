from pydantic import BaseModel
from typing import Optional

class AssetBase(BaseModel):
    name: str
    asset_type: str
    unique_id: str
    description: Optional[str] = None
    status: Optional[str] = "active"
    user_id: int

class AssetCreate(AssetBase):
    pass

class AssetUpdate(BaseModel):
    name: Optional[str] = None
    asset_type: Optional[str] = None
    unique_id: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    user_id: Optional[int] = None

class AssetResponse(AssetBase):
    id: int
    
    class Config:
        from_attributes = True