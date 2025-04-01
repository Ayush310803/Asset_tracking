import asyncio
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import os
from datetime import datetime
from typing import Dict
from app.services.export import FullDataExporter
from database import get_db_url
from app.auth import get_current_user, get_current_admin_user
from app.models.users_model import User

router = APIRouter(prefix="/export", tags=["Export"])

EXPORT_DIR = Path(__file__).parent.parent.parent / "exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

def cleanup_file(filepath: str):
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Error cleaning up {filepath}: {e}")

async def delayed_cleanup(filepath: str, delay: int = 3600):
    await asyncio.sleep(delay)
    cleanup_file(filepath)

@router.post("/full-export")
async def full_export(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin_user)
):
    try:
        exporter = FullDataExporter(db_url=get_db_url(), export_dir=EXPORT_DIR)
        exports = exporter.export_all_data()  
        
        for rel_path in exports.values():
            full_path = EXPORT_DIR / rel_path
            background_tasks.add_task(delayed_cleanup, str(full_path), 86400)
        
        return {
            "status": "success",
            "exports": {
                name: {
                    "filename": str(rel_path),
                    "download_url": f"/export/download/{rel_path}"
                } for name, rel_path in exports.items()
            }
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@router.post("/assets/{asset_id}")
async def export_asset_data(
    asset_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    try:
        exporter = FullDataExporter(db_url=get_db_url(), export_dir= EXPORT_DIR)
        rel_path = exporter.export_asset_data(asset_id)
        full_path = EXPORT_DIR / rel_path
        
        background_tasks.add_task(delayed_cleanup, str(full_path))
        
        return {
            "status": "success",
            "filename": str(rel_path),
            "download_url": f"/export/download/{rel_path}"
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@router.post("/assets_all/{asset_id}")
async def export_asset_data(
    asset_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    try:
        exporter = FullDataExporter(get_db_url(), EXPORT_DIR)
        filepath = exporter.export_asset_data_all(asset_id)
        
        background_tasks.add_task(delayed_cleanup, str(filepath))
        
        return {
            "status": "success",
            "filename": filepath.name,
            "download_url": f"/export/download/{filepath.relative_to(EXPORT_DIR)}"
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@router.get("/download/{filepath:path}")
async def download_export(
    filepath: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    try:
        if not filepath.endswith('.csv') or '..' in filepath:
            raise HTTPException(400, "Invalid file path")
        
        full_path = EXPORT_DIR / filepath
        
        try:
            full_path.resolve().relative_to(EXPORT_DIR.resolve())
        except ValueError:
            raise HTTPException(400, "Invalid file path")
        
        if not full_path.exists():
            available_files = []
            for root, _, files in os.walk(EXPORT_DIR):
                for f in files:
                    if f.endswith('.csv'):
                        rel_path = os.path.relpath(os.path.join(root, f), EXPORT_DIR)
                        available_files.append(rel_path)
            raise HTTPException(404, detail={
                "error": "File not found",
                "available_files": available_files
            })
        
        
        return FileResponse(
            full_path,
            media_type='text/csv',
            filename=full_path.name
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(500, detail=str(e))