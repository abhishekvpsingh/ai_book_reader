import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models import Book, Section, SectionAsset, Summary, SummaryVersion, AudioAsset, ReadingProgress

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def _safe_remove(path: str) -> None:
    if path and os.path.exists(path):
        os.remove(path)


def main() -> None:
    db = SessionLocal()
    try:
        books = db.query(Book).order_by(Book.id.asc()).all()
        seen = {}
        removed = []
        for book in books:
            key = (book.title, book.file_path)
            if key in seen:
                removed.append(book)
            else:
                seen[key] = book.id

        for book in removed:
            sections = db.query(Section).filter(Section.book_id == book.id).all()
            section_ids = [s.id for s in sections]
            assets = db.query(SectionAsset).filter(SectionAsset.book_id == book.id).all()

            for asset in assets:
                _safe_remove(asset.file_path)

            versions = (
                db.query(SummaryVersion)
                .join(Summary, SummaryVersion.summary_id == Summary.id)
                .filter(Summary.section_id.in_(section_ids))
                .all()
            )
            for version in versions:
                audio_assets = db.query(AudioAsset).filter(AudioAsset.version_id == version.id).all()
                for audio in audio_assets:
                    _safe_remove(audio.file_path)

            progress = db.query(ReadingProgress).filter(ReadingProgress.book_id == book.id).first()
            if progress:
                db.delete(progress)

            for version in versions:
                db.query(AudioAsset).filter(AudioAsset.version_id == version.id).delete()
            db.query(SummaryVersion).filter(SummaryVersion.summary_id.in_(
                [s.id for s in db.query(Summary).filter(Summary.section_id.in_(section_ids)).all()]
            )).delete(synchronize_session=False)
            db.query(Summary).filter(Summary.section_id.in_(section_ids)).delete(synchronize_session=False)
            db.query(SectionAsset).filter(SectionAsset.book_id == book.id).delete(synchronize_session=False)
            db.query(Section).filter(Section.book_id == book.id).delete(synchronize_session=False)

            _safe_remove(book.file_path)
            db.delete(book)

        db.commit()
        print(f"Removed {len(removed)} duplicate books")
    finally:
        db.close()


if __name__ == "__main__":
    main()
