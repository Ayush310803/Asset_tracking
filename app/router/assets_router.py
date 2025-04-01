from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models.users_model import User
from app.models.assets_model import Asset
from app.auth import get_current_admin_user, get_current_user
from database import get_db
from app.schemas.assets_schema import AssetResponse, AssetCreate, AssetUpdate
from app.crud.assets_crud import get_assets, create_asset, get_asset, update_asset, delete_asset

router = APIRouter()

@router.post("/assets/", response_model=AssetResponse)
def create_new_asset(asset: AssetCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    db_asset = db.query(Asset).filter(Asset.unique_id == asset.unique_id).first()
    if db_asset:
        raise HTTPException(status_code=400, detail="Asset with this unique_id already exists")
    
    new_asset = create_asset(db=db, asset_data=asset)

    return AssetResponse(
        id=new_asset.id,
        name=new_asset.name,
        asset_type=new_asset.asset_type,
        unique_id=new_asset.unique_id,
        description=new_asset.description,
        status=new_asset.status,
        user_id=new_asset.user_id
    )

@router.get("/assets/", response_model=List[AssetResponse])
def read_assets(skip: int = 0,limit: int = 100, db: Session = Depends(get_db),current_user: User = Depends(get_current_admin_user)):
    assets = get_assets(db, skip=skip, limit=limit)
    return assets

@router.get("/assets/{asset_id}", response_model=AssetResponse)
def read_asset(asset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_asset = get_asset(db, asset_id=asset_id)
    if db_asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return db_asset

@router.put("/assets/{asset_id}", response_model=AssetResponse)
def update_existing_asset(
    asset_id: int, 
    update_data: AssetUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_admin_user)
):
    db_asset = update_asset(db, asset_id, update_data)
    if db_asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return db_asset

@router.delete("/assets/{asset_id}")
def delete_existing_asset(asset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    db_asset = delete_asset(db, asset_id=asset_id)
    if db_asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": "Asset deleted successfully"}