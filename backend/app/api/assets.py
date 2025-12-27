import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import SectionAsset

router = APIRouter()


@router.get("/assets/{asset_id}")
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(SectionAsset, asset_id)
    if not asset or not os.path.exists(asset.file_path):
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(asset.file_path, media_type="image/png", filename=os.path.basename(asset.file_path))
