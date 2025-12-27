from datetime import datetime
from pydantic import BaseModel


class SummaryVersionOut(BaseModel):
    id: int
    summary_id: int
    version_number: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class SummaryGenerateResponse(BaseModel):
    job_id: str | None = None
    summary_version: SummaryVersionOut | None = None
    overview_only: str | None = None
    warning: str | None = None
