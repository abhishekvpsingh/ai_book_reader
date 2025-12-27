from fastapi import APIRouter
from app.api import books, sections, summaries, jobs, assets

api_router = APIRouter()
api_router.include_router(books.router, tags=["books"])
api_router.include_router(sections.router, tags=["sections"])
api_router.include_router(summaries.router, tags=["summaries"])
api_router.include_router(jobs.router, tags=["jobs"])
api_router.include_router(assets.router, tags=["assets"])
