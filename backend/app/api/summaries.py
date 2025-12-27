import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import SummaryVersion, AudioAsset
from app.schemas.summary import SummaryVersionOut
from app.services.tts_service import generate_audio
from app.workers.rq_queue import get_queue
from app.workers import tasks

router = APIRouter()


@router.get("/summary_versions/{version_id}", response_model=SummaryVersionOut)
def get_summary_version(version_id: int, db: Session = Depends(get_db)):
    version = db.get(SummaryVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Summary version not found")
    return version


@router.post("/summary_versions/{version_id}/tts")
def generate_tts(version_id: int):
    queue = get_queue()
    job = queue.enqueue(tasks.generate_tts_job, version_id)
    return {"job_id": job.id}


@router.get("/summary_versions/{version_id}/audio")
def get_audio(version_id: int, db: Session = Depends(get_db)):
    audio = (
        db.query(AudioAsset)
        .filter(AudioAsset.version_id == version_id)
        .order_by(AudioAsset.created_at.desc())
        .first()
    )
    if not audio or not os.path.exists(audio.file_path):
        raise HTTPException(status_code=404, detail="Audio not found")
    media_type = "audio/mpeg" if audio.format == "mp3" else "audio/wav"
    return FileResponse(audio.file_path, media_type=media_type, filename=os.path.basename(audio.file_path))


@router.delete("/summary_versions/{version_id}")
def delete_summary_version(version_id: int, db: Session = Depends(get_db)):
    version = db.get(SummaryVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Summary version not found")
    for audio in version.audio_assets:
        if os.path.exists(audio.file_path):
            os.remove(audio.file_path)
    db.delete(version)
    db.commit()
    return {"status": "deleted"}
