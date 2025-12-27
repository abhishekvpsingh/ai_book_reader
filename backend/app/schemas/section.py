from pydantic import BaseModel


class SectionOut(BaseModel):
    id: int
    book_id: int
    parent_id: int | None
    level: int
    title: str
    sort_order: int
    page_start: int
    page_end: int

    class Config:
        from_attributes = True


class SectionTree(BaseModel):
    id: int
    title: str
    level: int
    page_start: int
    page_end: int
    children: list["SectionTree"] = []

    class Config:
        from_attributes = True


SectionTree.model_rebuild()
