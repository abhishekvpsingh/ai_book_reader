import logging
from app.db.session import SessionLocal
from app.services.pdf_ingestion import ingest_pdf
from app.services.summary_service import generate_summary
from app.services.tts_service import generate_audio

logger = logging.getLogger(__name__)


def ingest_pdf_job(book_id: int) -> None:
    db = SessionLocal()
    try:
        ingest_pdf(db, book_id)
    finally:
        db.close()


def generate_summary_job(section_id: int, recursive: bool) -> int | None:
    db = SessionLocal()
    try:
        version, warning, overview = generate_summary(db, section_id, recursive)
        if warning or overview:
            logger.info("Large content warning", extra={"section_id": section_id})
            return {"warning": warning, "overview": overview}
        return version.id if version else None
    finally:
        db.close()


def generate_tts_job(version_id: int) -> int:
    db = SessionLocal()
    try:
        audio = generate_audio(db, version_id)
        return audio.id
    finally:
        db.close()
