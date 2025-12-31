from datetime import datetime
from pydantic import BaseModel, Field


class NoteCreate(BaseModel):
    page_num: int
    selection_text: str
    question: str
    answer: str
    rects: list[dict] = Field(default_factory=list)


class NoteOut(BaseModel):
    id: int
    book_id: int
    section_id: int | None
    page_num: int
    selection_text: str
    question: str
    answer: str
    rects: list[dict] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True
