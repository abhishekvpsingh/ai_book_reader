from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sections = relationship("Section", back_populates="book", cascade="all, delete-orphan")
    assets = relationship("SectionAsset", back_populates="book", cascade="all, delete-orphan")
    progress = relationship("ReadingProgress", back_populates="book", cascade="all, delete-orphan")
