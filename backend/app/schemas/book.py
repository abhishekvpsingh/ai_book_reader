from datetime import datetime
from pydantic import BaseModel


class BookCreate(BaseModel):
    title: str


class BookOut(BaseModel):
    id: int
    title: str
    created_at: datetime

    class Config:
        from_attributes = True
