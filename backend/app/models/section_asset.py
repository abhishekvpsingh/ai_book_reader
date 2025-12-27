from datetime import datetime
from sqlalchemy import String, ForeignKey, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class SectionAsset(Base):
    __tablename__ = "section_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True)
    section_id: Mapped[int | None] = mapped_column(ForeignKey("sections.id"), nullable=True, index=True)
    page_num: Mapped[int] = mapped_column(Integer)
    bbox: Mapped[str | None] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(1024))
    caption: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    book = relationship("Book", back_populates="assets")
    section = relationship("Section", back_populates="assets")
