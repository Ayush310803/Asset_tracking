from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from app.schemas.geo_schemas import GeoZoneCreate, GeoZoneResponse, GeoAlertResponse
from app.models.geo_models import GeoZone, GeoAlert
from app.models.locations_model import AssetLocation
from datetime import datetime
from sqlalchemy import func
from fastapi import HTTPException
from sqlalchemy import text
from geoalchemy2 import WKTElement

def create_geo_zone(db: Session, zone: GeoZoneCreate):
    coords = ",".join([f"{lon} {lat}" for lon, lat in zone.coordinates])
    wkt_polygon = f"SRID=4326;POLYGON(({coords}))"
    
    db_zone = GeoZone(
        asset_id=zone.asset_id,
        name=zone.name,
        zone=wkt_polygon
    )
    db.add(db_zone)
    db.commit()
    db.refresh(db_zone)

    result = db.execute(text(f"SELECT ST_AsText(zone) FROM geo_zones WHERE id = {db_zone.id}")).scalar()
    
    result = result.strip("POLYGON(()))")
    result_coords = result.split(",")

    coordinates = [[float(x) for x in coord.strip().split()] for coord in result_coords]

    return GeoZoneResponse(
        id=db_zone.id,
        asset_id=db_zone.asset_id,
        name=db_zone.name,
        coordinates=coordinates,
        created_at=db_zone.created_at
    )

def check_asset_in_zone(db: Session, asset_id: int):
    latest_location = db.query(
        AssetLocation,
        func.ST_X(AssetLocation.location).label("longitude"),
        func.ST_Y(AssetLocation.location).label("latitude")
    ).filter(
        AssetLocation.asset_id == asset_id
    ).order_by(
        AssetLocation.timestamp.desc()
    ).first()

    if not latest_location:
        raise HTTPException(status_code=404, detail="No recent location found for asset")

    _, longitude, latitude = latest_location

    query = text("""
        SELECT COUNT(*)
        FROM geo_zones
        WHERE asset_id = :asset_id
        AND ST_Contains(zone, ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326))
    """)

    result = db.execute(query, {
        "asset_id": asset_id,
        "longitude": longitude,
        "latitude": latitude
    }).scalar()

    return bool(result), longitude, latitude

def is_valid_coordinate(lat, lon):
    return -90 <= lat <= 90 and -180 <= lon <= 180

def create_geo_alert(db: Session, asset_id: int, alert_type: str, message: str):
    latest_location = db.query(AssetLocation).filter(
        AssetLocation.asset_id == asset_id
    ).order_by(
        AssetLocation.timestamp.desc()
    ).first()

    if not latest_location:
        raise HTTPException(status_code=404, detail="No recent location found for asset")
    
    query = db.execute(
        text("SELECT ST_Y(location), ST_X(location) FROM asset_locations WHERE id = :id"),
        {"id": latest_location.id}
    )
    latitude, longitude = query.fetchone()

    if not is_valid_coordinate(latitude, longitude):
        raise HTTPException(status_code=400, detail="Invalid latitude or longitude values.")
    
    db_alert = GeoAlert(
        asset_id=asset_id,
        alert_type=alert_type,
        message=message,
        triggered_at=datetime.utcnow(),
        resolved=False,
    )
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)

    return GeoAlertResponse(
        id=db_alert.id,
        asset_id=db_alert.asset_id,
        alert_type=db_alert.alert_type,
        message=db_alert.message,
        latitude=latitude,
        longitude=longitude,
        triggered_at=db_alert.triggered_at,
        resolved=db_alert.resolved,
    )


