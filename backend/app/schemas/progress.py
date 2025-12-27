from datetime import datetime
from pydantic import BaseModel


class ProgressOut(BaseModel):
    book_id: int
    last_page: int
    last_section_id: int | None
    updated_at: datetime

    class Config:
        from_attributes = True


class ProgressUpdate(BaseModel):
    last_page: int
    last_section_id: int | None = None
