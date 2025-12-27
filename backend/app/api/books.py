import logging
from datetime import datetime
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Book, Section, ReadingProgress
from app.schemas.book import BookOut
from app.schemas.section import SectionTree
from app.schemas.progress import ProgressOut, ProgressUpdate
from app.services.pdf_ingestion import save_pdf_file
from app.services.section_tree_builder import build_tree
from app.workers.rq_queue import get_queue
from app.workers import tasks

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/books", response_model=BookOut)
async def upload_book(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    content = await file.read()
    book = Book(title=file.filename, file_path="")
    db.add(book)
    db.flush()
    file_path = save_pdf_file(book.id, file.filename, content)
    book.file_path = file_path
    db.commit()
    db.refresh(book)

    queue = get_queue()
    job = queue.enqueue(tasks.ingest_pdf_job, book.id)
    logger.info("Book uploaded", extra={"book_id": book.id, "job_id": job.id})
    return book


@router.get("/books", response_model=list[BookOut])
def list_books(db: Session = Depends(get_db)):
    return db.query(Book).order_by(Book.created_at.desc()).all()


@router.get("/books/{book_id}", response_model=BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.get("/books/{book_id}/sections", response_model=list[SectionTree])
def get_book_sections(book_id: int, db: Session = Depends(get_db)):
    sections = db.query(Section).filter(Section.book_id == book_id).order_by(Section.sort_order).all()
    return build_tree(sections)


@router.get("/books/{book_id}/pdf")
def get_book_pdf(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    headers = {
        "Content-Disposition": "inline",
        "Content-Security-Policy": "frame-ancestors *",
        "X-Frame-Options": "ALLOWALL",
    }
    return FileResponse(book.file_path, media_type="application/pdf", headers=headers)


@router.get("/books/{book_id}/progress", response_model=ProgressOut)
def get_progress(book_id: int, db: Session = Depends(get_db)):
    progress = db.query(ReadingProgress).filter(ReadingProgress.book_id == book_id).first()
    if not progress:
        raise HTTPException(status_code=404, detail="Progress not found")
    return progress


@router.put("/books/{book_id}/progress", response_model=ProgressOut)
def update_progress(book_id: int, payload: ProgressUpdate, db: Session = Depends(get_db)):
    progress = db.query(ReadingProgress).filter(ReadingProgress.book_id == book_id).first()
    if not progress:
        progress = ReadingProgress(book_id=book_id, last_page=payload.last_page, last_section_id=payload.last_section_id)
        db.add(progress)
    else:
        progress.last_page = payload.last_page
        progress.last_section_id = payload.last_section_id
        progress.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(progress)
    return progress
