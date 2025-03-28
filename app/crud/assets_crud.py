from sqlalchemy.orm import Session
from app.models.assets_model import Asset
from app.schemas.assets_schema import AssetCreate, AssetUpdate

def get_asset(db: Session, asset_id: int):
    return db.query(Asset).filter(Asset.id == asset_id).first()

def get_assets(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Asset).offset(skip).limit(limit).all()

def create_asset(db: Session, asset_data: AssetCreate):
    db_asset = Asset(**asset_data.dict())
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset

def update_asset(db: Session, asset_id: int, update_data: AssetUpdate):
    db_asset = get_asset(db, asset_id)
    if not db_asset:
        return None

    if update_data.name is not None:
        db_asset.name = update_data.name
    if update_data.asset_type is not None:
        db_asset.asset_type = update_data.asset_type
    if update_data.unique_id is not None:
        db_asset.unique_id = update_data.unique_id
    if update_data.description is not None:
        db_asset.description = update_data.description
    if update_data.status is not None:
        db_asset.status = update_data.status
    if update_data.user_id is not None:
        db_asset.user_id = update_data.user_id

    db.commit()
    db.refresh(db_asset)

    return db_asset

def delete_asset(db: Session, asset_id: int):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if asset:
        db.delete(asset)
        db.commit()
    return asset