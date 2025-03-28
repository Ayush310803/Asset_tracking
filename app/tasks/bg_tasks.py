from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal
from app.models.locations_model import AssetLocation
from app.models.assets_model import Asset
from app.models.geo_models import GeoAlert, GeoZone
from sqlalchemy import func
from sqlalchemy.sql import and_
from app.crud.geo_crud import create_geo_alert
from sqlalchemy.sql import text
from typing import List

def get_stale_assets(db: Session) -> List[Asset]:
    threshold = datetime.utcnow() - timedelta(minutes=10)
    
    recent_assets_subq = db.query(
        AssetLocation.asset_id
    ).filter(
        AssetLocation.timestamp >= threshold
    ).distinct().subquery()
    
    return db.query(Asset).filter(
        ~Asset.id.in_(db.query(recent_assets_subq.c.asset_id))
    ).all()

def check_asset_in_zone1(db: Session, asset_id: int):
    latest_location = db.query(
        AssetLocation.location
    ).filter(
        AssetLocation.asset_id == asset_id
    ).order_by(
        AssetLocation.timestamp.desc()
    ).first()

    if not latest_location:
        return False, None, None  

    zone_exists = db.query(GeoZone).filter(
        GeoZone.asset_id == asset_id,
        func.ST_Contains(GeoZone.zone, latest_location.location)
    ).first()

    coords = None
    if zone_exists:
        coords = db.query(
            func.ST_X(latest_location.location),
            func.ST_Y(latest_location.location)
        ).first()

    return bool(zone_exists), coords[0] if coords else None, coords[1] if coords else None

def check_geo_fences():
    db = SessionLocal()
    try:

        subquery = db.query(
            AssetLocation.asset_id,
            func.max(AssetLocation.timestamp).label('max_time')
        ).group_by(
            AssetLocation.asset_id
        ).subquery()

        latest_locations = db.query(AssetLocation).join(
            subquery,
            and_(
                AssetLocation.asset_id == subquery.c.asset_id,
                AssetLocation.timestamp == subquery.c.max_time
            )
        ).all()

        for location in latest_locations:
            in_zone, lon, lat = check_asset_in_zone1(db, location.asset_id)
            if not in_zone:
                create_geo_alert(
                    db,
                    location.asset_id,
                    "exit_zone",
                    f"Asset {location.asset_id} exited geo-fence at {lon},{lat}"
                )
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def check_stale_locations():
    db = SessionLocal()
    try:
        stale_assets = get_stale_assets(db)
        for asset in stale_assets:
            create_geo_alert(
                db,
                asset.id,
                "stale_data",
                f"Asset {asset.id} has no updates for 10+ minutes"
            )
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()