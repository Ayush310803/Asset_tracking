from sqlalchemy.orm import Session
from geoalchemy2.functions import ST_Point
from datetime import datetime
from app.models.locations_model import AssetLocation
from app.schemas.locations_schema import LocationCreate, LocationResponse
from sqlalchemy import text

def create_asset_location(db: Session, asset_id: int, location: LocationCreate):
    point = f"SRID=4326;POINT({location.longitude} {location.latitude})"
    db_location = AssetLocation(
        asset_id=asset_id,
        location=point,
        timestamp=location.timestamp or datetime.utcnow(),
        additional_data=location.additional_data or {}
    )
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location

def get_latest_asset_location(db: Session, asset_id: int):
    result = db.execute(
        text("""
            SELECT id, asset_id, ST_X(location) AS longitude, ST_Y(location) AS latitude, timestamp, additional_data
            FROM asset_locations
            WHERE asset_id = :asset_id
            ORDER BY timestamp DESC
            LIMIT 1
        """),
        {"asset_id": asset_id}
    ).mappings().first()
    
    if result:
        return LocationResponse(**result)
    return None

def get_asset_location_history(db: Session, asset_id: int, start_time: datetime = None, end_time: datetime = None, limit: int = 100):
    query = text("""
        SELECT id, asset_id, ST_X(location) AS longitude, ST_Y(location) AS latitude, timestamp, additional_data
        FROM asset_locations
        WHERE asset_id = :asset_id
        {start_filter}
        {end_filter}
        ORDER BY timestamp DESC
        LIMIT :limit
    """.format(
        start_filter="AND timestamp >= :start_time" if start_time else "",
        end_filter="AND timestamp <= :end_time" if end_time else ""
    ))

    params = {"asset_id": asset_id, "limit": limit}
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time

    results = db.execute(query, params).mappings().all()

    return [LocationResponse(**row) for row in results]