from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, Request, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from app.models.users_model import User, Role
from datetime import timedelta
from database import Base, engine
from app.router import assets_router, locations_router, auth_router, geo_router, export_router
from fastapi.middleware.cors import CORSMiddleware
from fastapi_utils.tasks import repeat_every
from database import Base, engine
from app.tasks.bg_tasks import check_geo_fences, check_stale_locations
from datetime import datetime
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from database import get_db
from app.auth import get_current_admin_user,get_current_user
from typing import Optional 
from app.models.assets_model import Asset
from app.crud.locations_crud import create_asset_location, get_latest_asset_location, get_asset_location_history
from fastapi.responses import JSONResponse
from sqlalchemy import text
from fastapi import WebSocket, WebSocketDisconnect
from app.schemas.locations_schema import LocationResponse
import asyncio
from database import SessionLocal

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(assets_router.router, prefix="/api/v1", tags=["assets"])
app.include_router(locations_router.router, prefix="/api/v1")
app.include_router(geo_router.router, prefix="/api/v1")
app.include_router(export_router.router, prefix="/api/v1")

@app.on_event("startup")
@repeat_every(seconds=60 * 5)  
def run_geo_checks():
    try:
        print("Geo checks started at:", datetime.now())
        check_geo_fences()
        check_stale_locations()
    except Exception as e:
        print(f"Error in run_geo_checks: {e}")
    finally:
        print("Geo checks completed at:", datetime.now())

class WebSocketManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, asset_id: int):
        await websocket.accept()
        if asset_id not in self.active_connections:
            self.active_connections[asset_id] = []
        self.active_connections[asset_id].append(websocket)

    def disconnect(self, websocket: WebSocket, asset_id: int):
        if asset_id in self.active_connections:
            self.active_connections[asset_id].remove(websocket)
            if not self.active_connections[asset_id]:
                del self.active_connections[asset_id]
    
    async def send_message(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_json(message)
        except Exception as e:
            self.disconnect(websocket, message.get("asset_id"))
            print(f"Error sending message: {e}")


    async def broadcast(self, asset_id: int, message: str):
        if asset_id in self.active_connections:
            for connection in self.active_connections[asset_id]:
                await connection.send_text(message)

manager = WebSocketManager()

async def track_asset_location(asset_id: int):
    while True:
        db = SessionLocal()
        try:
            location_data = get_latest_asset_location(db, asset_id)
            if location_data:
                # Check if it's a Pydantic model or a dictionary
                if isinstance(location_data, LocationResponse):
                    await manager.broadcast(asset_id, location_data.model_dump())
                else:
                    await manager.broadcast(asset_id, dict(location_data))
            await asyncio.sleep(2)  # Adjust interval as needed
        except Exception as e:
            print(f"Error in tracking: {e}")
        finally:
            db.close()

@app.get("/track/{asset_id}", response_class=HTMLResponse)
async def track_asset(request: Request, asset_id: int):
    return templates.TemplateResponse("track.html", {
        "request": request,
        "asset_id": asset_id
    })

@app.websocket("/ws/track/{asset_id}")
async def websocket_tracking(websocket: WebSocket, asset_id: int):
    await manager.connect(websocket, asset_id)
    asyncio.create_task(track_asset_location(asset_id))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, asset_id)

from pydantic import BaseModel
from datetime import datetime

class AssetLocationResponse(BaseModel):
    id: int
    latitude: float
    longitude: float
    timestamp: datetime

    class Config:
        from_attributes = True


@app.get("/{asset_id}/history-page", response_class=HTMLResponse)
def get_history_page(
    asset_id: int,
    request: Request,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    # Check if asset exists
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Get asset location history
    locations = get_asset_location_history(
        db,
        asset_id=asset_id,
        start_time=start_time,
        end_time=end_time,
        limit=1000
    )

    data = [
    AssetLocationResponse(
        id=loc.id,
        latitude=loc.latitude,
        longitude=loc.longitude,
        timestamp=loc.timestamp.isoformat() if isinstance(loc.timestamp, datetime) else loc.timestamp
    ).dict()  
    for loc in locations
    ]


    return templates.TemplateResponse(
    "history.html",
    {
        "request": request,
        "asset_id": asset_id,
        "history": data,
        "start_time": start_time.isoformat() if start_time else "",
        "end_time": end_time.isoformat() if end_time else ""
    }
)


