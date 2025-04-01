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
from app.models.locations_model import AssetLocation
from app.crud.locations_crud import create_asset_location, get_latest_asset_location, get_asset_location_history
from fastapi.responses import JSONResponse
from sqlalchemy import text
from fastapi import WebSocket, WebSocketDisconnect
from app.schemas.locations_schema import LocationResponse
import asyncio
from database import SessionLocal
import aiohttp
import json

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
        self.tracking_tasks = {}  

    async def connect(self, websocket: WebSocket, asset_id: int):
        await websocket.accept()
        if asset_id not in self.active_connections:
            self.active_connections[asset_id] = []
           
            self.tracking_tasks[asset_id] = asyncio.create_task(
                self.track_asset_location(asset_id)
            )
        self.active_connections[asset_id].append(websocket)

    def disconnect(self, websocket: WebSocket, asset_id: int):
        if asset_id in self.active_connections:
            self.active_connections[asset_id].remove(websocket)
            if not self.active_connections[asset_id]:
                del self.active_connections[asset_id]
                
                self.tracking_tasks[asset_id].cancel()
                del self.tracking_tasks[asset_id]

    async def track_asset_location(self, asset_id: int):
        while True:
            try:
                db: Session = next(get_db())
                location_data = get_latest_asset_location(db, asset_id)

                if location_data:
                    location_dict = location_data.dict()
                    location_dict['timestamp'] = location_dict['timestamp'].isoformat()
                    await self.broadcast(asset_id, location_dict)
                else:
                    print(f"No location data found for asset {asset_id}")

                await asyncio.sleep(2)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Tracking error: {e}")
                await asyncio.sleep(2)

    async def broadcast(self, asset_id: int, message: dict):
        if asset_id in self.active_connections:
            for connection in self.active_connections[asset_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error sending message: {e}")
                    self.disconnect(connection, asset_id)

manager = WebSocketManager()

@app.get("/track/{asset_id}", response_class=HTMLResponse)
async def track_asset(request: Request, asset_id: int):
    return templates.TemplateResponse("track.html", {
        "request": request,
        "asset_id": asset_id
    })

@app.websocket("/ws/track/{asset_id}")
async def websocket_tracking(websocket: WebSocket, asset_id: int):
    await manager.connect(websocket, asset_id)
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

from sqlalchemy import func
from geoalchemy2 import functions as geofunc

@app.get("/{asset_id}/history-page", response_class=HTMLResponse)
def get_history_page(
    asset_id: int,
    request: Request,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    query = db.query(
        AssetLocation.id,
        geofunc.ST_Y(AssetLocation.location).label('latitude'),
        geofunc.ST_X(AssetLocation.location).label('longitude'),
        AssetLocation.timestamp,
        AssetLocation.additional_data
    ).filter(AssetLocation.asset_id == asset_id)

    if start_time:
        query = query.filter(AssetLocation.timestamp >= start_time)
    if end_time:
        query = query.filter(AssetLocation.timestamp <= end_time)
    
    locations = query.order_by(AssetLocation.timestamp).limit(1000).all()

    history = []
    for loc in locations:
        try:
            history.append({
                "id": loc.id,
                "latitude": float(loc.latitude),
                "longitude": float(loc.longitude),
                "timestamp": loc.timestamp.isoformat(),
                "additional_data": loc.additional_data
            })
        except Exception as e:
            print(f"Error processing location {loc.id}: {str(e)}")
            continue

    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "asset_id": asset_id,
            "history": history,
            "start_time": start_time.isoformat() if start_time else "",
            "end_time": end_time.isoformat() if end_time else "",
            "point_count": len(history)
        }
    )

@app.get("/test-websocket/{asset_id}")
async def test_websocket_page(request: Request, asset_id: int):
    return HTMLResponse(f"""
    <html>
    <body>
        <h1>WebSocket Test for Asset {asset_id}</h1>
        <div id="output"></div>
        <script>
            const socket = new WebSocket(`ws://${{window.location.host}}/ws/track/{asset_id}`);
            
            socket.onopen = () => {{
                document.getElementById('output').innerHTML += '<p>Connected!</p>';
            }};
            
            socket.onmessage = (event) => {{
                document.getElementById('output').innerHTML += `<p>Received: ${{event.data}}</p>`;
            }};
            
            socket.onclose = () => {{
                document.getElementById('output').innerHTML += '<p>Disconnected</p>';
            }};
        </script>
    </body>
    </html>
    """)

