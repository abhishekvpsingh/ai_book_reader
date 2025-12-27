from sqlalchemy import String, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Section(Base):
    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("sections.id"), nullable=True, index=True)
    level: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(512))
    sort_order: Mapped[int] = mapped_column(Integer)
    page_start: Mapped[int] = mapped_column(Integer)
    page_end: Mapped[int] = mapped_column(Integer)

    book = relationship("Book", back_populates="sections")
    parent = relationship("Section", remote_side=[id], backref="children")
    assets = relationship("SectionAsset", back_populates="section", cascade="all, delete-orphan")
    summaries = relationship("Summary", back_populates="section", cascade="all, delete-orphan")
