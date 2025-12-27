from datetime import datetime
from pydantic import BaseModel


class SectionAssetOut(BaseModel):
    id: int
    section_id: int | None
    page_num: int
    file_path: str
    caption: str
    created_at: datetime

    class Config:
        from_attributes = True
