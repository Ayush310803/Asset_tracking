from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from database import get_db
from app.models.users_model import User
from app.auth import get_current_user
from app.schemas.locations_schema import LocationCreate, LocationResponse
from app.crud.locations_crud import create_asset_location, get_latest_asset_location, get_asset_location_history
from sqlalchemy import text

router = APIRouter(prefix="/track", tags=["tracking"])

@router.post("/{asset_id}", response_model=LocationResponse)
def post_location_update(asset_id: int,location: LocationCreate,db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    db_location = create_asset_location(db, asset_id=asset_id, location=location)
    if not db_location:
        raise HTTPException(status_code=404, detail="Failed to create asset location")
    
    result = db.execute(
    text("SELECT ST_X(location), ST_Y(location) FROM asset_locations WHERE id = :id"),
    {"id": db_location.id}).fetchone()

    if result:
        db_location.longitude, db_location.latitude = result
    else:
        raise HTTPException(status_code=500, detail="Failed to fetch location data")
    return db_location

@router.get("/{asset_id}", response_model=LocationResponse)
def get_latest_location(asset_id: int,db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    location = get_latest_asset_location(db, asset_id=asset_id)
    if not location:
        raise HTTPException(status_code=404, detail="No location data found for this asset")
    return location

@router.get("/{asset_id}/history", response_model=list[LocationResponse])
def get_location_history(
    asset_id: int,
    start_time: Optional[datetime] = Query(None, description="Start time for history range"),
    end_time: Optional[datetime] = Query(None, description="End time for history range"),
    limit: Optional[int] = Query(100, description="Limit number of results"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_asset_location_history(
        db,
        asset_id=asset_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit
    )