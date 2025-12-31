from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from app.models.base import Base


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True, index=True)
    page_num = Column(Integer, nullable=False, index=True)
    selection_text = Column(Text, nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    rects_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
