import pandas as pd
from sqlalchemy import create_engine
from pathlib import Path
from datetime import datetime
import os
from typing import Dict

class FullDataExporter:
    def __init__(self, db_url: str, export_dir: Path):
        self.engine = create_engine(db_url)
        self.export_dir = export_dir
        os.makedirs(self.export_dir, exist_ok=True)
    
    def export_all_data(self) -> Dict[str, str]:
        full_dir = self.export_dir / "full"
        full_dir.mkdir(exist_ok=True)
        
        for f in full_dir.glob("*.csv"):
            f.unlink()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        exports = {}
        
        try:
            users_df = pd.read_sql_table("users", self.engine)
            users_path = full_dir / f"users_{timestamp}.csv"
            users_df.to_csv(users_path, index=False)
            exports['users'] = users_path.relative_to(self.export_dir)
            
            assets_df = pd.read_sql_table("assets", self.engine)
            assets_path = full_dir / f"assets_{timestamp}.csv"
            assets_df.to_csv(assets_path, index=False)
            exports['assets'] = assets_path.relative_to(self.export_dir)
            
            loc_df = pd.read_sql_query(
                "SELECT id, asset_id, ST_X(location) as longitude, "
                "ST_Y(location) as latitude, timestamp, additional_data "
                "FROM asset_locations", self.engine
            )
            loc_path = full_dir / f"locations_{timestamp}.csv"
            loc_df.to_csv(loc_path, index=False)
            exports['locations'] = loc_path.relative_to(self.export_dir)
            
            return exports
        except Exception as e:
            for path in exports.values():
                (self.export_dir / path).unlink(missing_ok=True)
            raise
    
    def export_asset_data(self, asset_id: int) -> str:
        asset_dir = self.export_dir / "assets" / str(asset_id)
        asset_dir.mkdir(parents=True, exist_ok=True)
        
        for f in asset_dir.glob("*.csv"):
            f.unlink()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = asset_dir / f"asset_{asset_id}_{timestamp}.csv"
        
        query = f"""
            SELECT a.id, a.name, 
                   ST_X(al.location) as longitude, 
                   ST_Y(al.location) as latitude,
                   al.timestamp, al.additional_data
            FROM assets a
            LEFT JOIN asset_locations al ON a.id = al.asset_id
            WHERE a.id = {asset_id}
            ORDER BY al.timestamp DESC
        """
        df = pd.read_sql_query(query, self.engine)
        df.to_csv(filepath, index=False)
        
        return filepath.relative_to(self.export_dir)

    def export_asset_data_all(self, asset_id: int) -> Path:
        asset_dir = self.export_dir / "assets_all" / str(asset_id)
        asset_dir.mkdir(parents=True, exist_ok=True)
        
        for f in asset_dir.glob("*.csv"):
            f.unlink()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = asset_dir / f"asset_{asset_id}combined{timestamp}.csv"

        query = f"""
            SELECT 
                'location' AS record_type,
                al.id AS record_id,
                ST_X(al.location) AS longitude,
                ST_Y(al.location) AS latitude,
                al.timestamp,
                al.additional_data,
                NULL AS alert_type,
                NULL AS message,
                NULL AS resolution_status
            FROM asset_locations al
            WHERE al.asset_id = {asset_id}

            UNION ALL

            SELECT 
                'alert' AS record_type,
                ga.id AS record_id,
                ST_X(ST_Centroid(gz.zone)) AS longitude,  -- Get zone center
                ST_Y(ST_Centroid(gz.zone)) AS latitude,
                ga.triggered_at AS timestamp,
                NULL AS additional_data,
                ga.alert_type,
                ga.message,
                ga.resolved AS resolution_status
            FROM geo_alerts ga
            JOIN geo_zones gz ON ga.asset_id = gz.asset_id
            WHERE ga.asset_id = {asset_id}

            ORDER BY timestamp DESC
        """

        df = pd.read_sql_query(query, self.engine)
        df.to_csv(filepath, index=False)
        
        return filepath