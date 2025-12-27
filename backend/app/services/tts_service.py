import hashlib
import logging
import os
import subprocess
from datetime import datetime
from gtts import gTTS
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import AudioAsset, SummaryVersion

logger = logging.getLogger(__name__)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ensure_dirs(book_id: int, section_id: int) -> str:
    path = os.path.join(settings.audio_dir, str(book_id), str(section_id))
    os.makedirs(path, exist_ok=True)
    return path


def _generate_with_piper(text: str, output_path: str) -> None:
    if not settings.piper_bin or not settings.piper_model:
        if settings.tts_allow_network:
            logger.warning("Piper not configured; falling back to gTTS")
            _generate_with_gtts(text, output_path.replace(".wav", ".mp3"))
            return
        raise RuntimeError("Piper backend requires PIPER_BIN and PIPER_MODEL or enable gTTS fallback")
    cmd = [settings.piper_bin, "--model", settings.piper_model, "--output_file", output_path]
    subprocess.run(cmd, input=text.encode("utf-8"), check=True)


def _generate_with_gtts(text: str, output_path: str) -> None:
    if not settings.tts_allow_network:
        raise RuntimeError("gTTS requires network access; set TTS_ALLOW_NETWORK=true")
    tts = gTTS(text=text, lang=settings.tts_lang)
    tts.save(output_path)


def generate_audio(db: Session, version_id: int) -> AudioAsset:
    version = db.get(SummaryVersion, version_id)
    if not version:
        raise ValueError("Summary version not found")

    content_hash = _hash_text(version.content)
    existing = (
        db.query(AudioAsset)
        .filter(AudioAsset.version_id == version_id)
        .filter(AudioAsset.content_hash == content_hash)
        .first()
    )
    if existing:
        return existing

    section_id = version.summary.section_id
    book_id = version.summary.section.book_id
    dir_path = _ensure_dirs(book_id, section_id)

    fmt = "wav" if settings.tts_backend == "piper" else "mp3"
    file_path = os.path.join(dir_path, f"{version_id}.{fmt}")

    if settings.tts_backend == "piper":
        _generate_with_piper(version.content, file_path)
        if not os.path.exists(file_path):
            fmt = "mp3"
            file_path = os.path.join(dir_path, f"{version_id}.{fmt}")
    elif settings.tts_backend == "gtts":
        _generate_with_gtts(version.content, file_path)
    else:
        raise RuntimeError(f"Unsupported TTS backend: {settings.tts_backend}")

    audio = AudioAsset(
        version_id=version_id,
        content_hash=content_hash,
        file_path=file_path,
        format=fmt,
        created_at=datetime.utcnow(),
    )
    db.add(audio)
    db.commit()
    db.refresh(audio)
    logger.info("Audio generated", extra={"version_id": version_id, "file_path": file_path})
    return audio
