import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Book, Note, Section
from app.schemas.note import NoteCreate, NoteOut
from app.schemas.section import SectionOut
from app.services.qa_service import answer_question

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/books/{book_id}/sections/by_page", response_model=SectionOut)
def get_section_by_page(book_id: int, page: int = Query(..., ge=1), db: Session = Depends(get_db)):
    section = (
        db.query(Section)
        .filter(Section.book_id == book_id, Section.page_start <= page, Section.page_end >= page)
        .order_by((Section.page_end - Section.page_start).asc())
        .first()
    )
    if not section:
        raise HTTPException(status_code=404, detail="Section not found for page")
    return section


@router.post("/books/{book_id}/qa")
def ask_question(book_id: int, payload: dict, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    selection_text = (payload.get("selection_text") or "").strip()
    question = (payload.get("question") or "").strip()
    if not selection_text or not question:
        raise HTTPException(status_code=400, detail="selection_text and question are required")
    answer = answer_question(selection_text, question)
    return {"answer": answer}


@router.post("/books/{book_id}/notes", response_model=NoteOut)
def create_note(book_id: int, note_in: NoteCreate, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    section = (
        db.query(Section)
        .filter(Section.book_id == book_id, Section.page_start <= note_in.page_num, Section.page_end >= note_in.page_num)
        .order_by((Section.page_end - Section.page_start).asc())
        .first()
    )
    note = Note(
        book_id=book_id,
        section_id=section.id if section else None,
        page_num=note_in.page_num,
        selection_text=note_in.selection_text,
        question=note_in.question,
        answer=note_in.answer,
        rects_json=json.dumps(note_in.rects),
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return _note_out(note)


@router.get("/books/{book_id}/notes", response_model=list[NoteOut])
def list_notes(book_id: int, page: int | None = Query(None, ge=1), db: Session = Depends(get_db)):
    query = db.query(Note).filter(Note.book_id == book_id)
    if page is not None:
        query = query.filter(Note.page_num == page)
    notes = query.order_by(Note.created_at.desc()).all()
    return [_note_out(note) for note in notes]


def _note_out(note: Note) -> NoteOut:
    rects = []
    if note.rects_json:
        try:
            rects = json.loads(note.rects_json)
        except json.JSONDecodeError:
            rects = []
    return NoteOut(
        id=note.id,
        book_id=note.book_id,
        section_id=note.section_id,
        page_num=note.page_num,
        selection_text=note.selection_text,
        question=note.question,
        answer=note.answer,
        rects=rects,
        created_at=note.created_at,
    )
