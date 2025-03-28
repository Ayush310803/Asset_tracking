from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from app.models.users_model import User
from app.models.geo_models import GeoAlert, GeoZone
from app.schemas.geo_schemas import GeoZoneCreate, GeoZoneResponse, GeoAlertResponse
from app.crud.geo_crud import create_geo_zone, check_asset_in_zone, create_geo_alert
from app.auth import get_current_admin_user,get_current_user
from sqlalchemy.sql import text

router = APIRouter(prefix="/geo", tags=["geo-fencing"])

@router.post("/geofence", response_model=GeoZoneResponse)
def create_zone(
    zone: GeoZoneCreate,
    db: Session = Depends(get_db),  current_user: User = Depends(get_current_user)
):
    return create_geo_zone(db, zone)

@router.get("/check/{asset_id}", response_model=GeoAlertResponse)
def check_location(asset_id: int, db: Session = Depends(get_db)):
    try:
        alert_response = create_geo_alert(
            db,
            asset_id,
            "Geo-fence Breach",
            "Asset has exited the designated zone."
        )
        return alert_response
    
    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts/{asset_id}", response_model=List[GeoAlertResponse])
def get_asset_alerts(asset_id: int, db: Session = Depends(get_db)):
    query = text("""
        SELECT ga.id, ga.asset_id, ga.alert_type, ga.message, 
               ST_Y(al.location) AS latitude, ST_X(al.location) AS longitude, 
               ga.triggered_at, ga.resolved
        FROM geo_alerts ga
        JOIN asset_locations al ON al.asset_id = ga.asset_id
        WHERE ga.asset_id = :asset_id
        ORDER BY ga.triggered_at DESC
    """)

    result = db.execute(query, {"asset_id": asset_id}).fetchall()

    return [
        GeoAlertResponse(
            id=row.id,
            asset_id=row.asset_id,
            alert_type=row.alert_type,
            message=row.message,
            latitude=row.latitude,
            longitude=row.longitude,
            triggered_at=row.triggered_at,
            resolved=row.resolved
        ) for row in result
    ]

    
