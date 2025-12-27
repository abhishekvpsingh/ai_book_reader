from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Section, Summary, SummaryVersion, SectionAsset
from app.schemas.section import SectionOut
from app.schemas.summary import SummaryGenerateResponse, SummaryVersionOut
from app.schemas.asset import SectionAssetOut
from app.services.summary_service import generate_summary
from app.workers.rq_queue import get_queue
from app.workers import tasks

router = APIRouter()


@router.get("/sections/{section_id}", response_model=SectionOut)
def get_section(section_id: int, db: Session = Depends(get_db)):
    section = db.get(Section, section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    return section


@router.post("/sections/{section_id}/summaries:generate", response_model=SummaryGenerateResponse)
def generate_section_summary(
    section_id: int,
    recursive: bool = Query(False),
    db: Session = Depends(get_db),
):
    queue = get_queue()
    job = queue.enqueue(tasks.generate_summary_job, section_id, recursive)
    return SummaryGenerateResponse(job_id=job.id)


@router.get("/sections/{section_id}/summary_versions", response_model=list[SummaryVersionOut])
def list_summary_versions(section_id: int, db: Session = Depends(get_db)):
    summary = db.query(Summary).filter(Summary.section_id == section_id).first()
    if not summary:
        return []
    versions = (
        db.query(SummaryVersion)
        .filter(SummaryVersion.summary_id == summary.id)
        .order_by(SummaryVersion.version_number.desc())
        .all()
    )
    return versions


def _collect_descendants(section: Section) -> list[Section]:
    nodes = [section]
    result = []
    while nodes:
        node = nodes.pop(0)
        result.append(node)
        nodes.extend(node.children)
    return result


@router.get("/sections/{section_id}/assets", response_model=list[SectionAssetOut])
def list_section_assets(section_id: int, recursive: bool = False, db: Session = Depends(get_db)):
    section = db.get(Section, section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    sections = _collect_descendants(section) if recursive else [section]
    section_ids = [sec.id for sec in sections]
    return (
        db.query(SectionAsset)
        .filter(SectionAsset.section_id.in_(section_ids))
        .order_by(SectionAsset.page_num)
        .all()
    )
