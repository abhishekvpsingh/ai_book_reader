import logging
import os
import fitz
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import Book, Section, SectionAsset, ReadingProgress
from app.services.section_tree import build_sections_from_toc, infer_sections_from_headings, compute_page_ranges
from app.services.image_extraction import extract_images

logger = logging.getLogger(__name__)


def ingest_pdf(db: Session, book_id: int) -> None:
    book = db.get(Book, book_id)
    if not book:
        raise ValueError("Book not found")

    doc = fitz.open(book.file_path)
    toc_nodes = build_sections_from_toc(doc)
    if not toc_nodes:
        logger.info("No TOC found; inferring sections")
        toc_nodes = infer_sections_from_headings(doc)

    ranges = compute_page_ranges(toc_nodes, doc.page_count)

    section_stack: list[Section] = []
    for sort_order, (node, start, end) in enumerate(ranges, start=1):
        while section_stack and section_stack[-1].level >= node.level:
            section_stack.pop()
        parent_id = section_stack[-1].id if section_stack else None
        section = Section(
            book_id=book_id,
            parent_id=parent_id,
            level=node.level,
            title=node.title,
            sort_order=sort_order,
            page_start=start,
            page_end=end,
        )
        db.add(section)
        db.flush()
        section_stack.append(section)

    assets = extract_images(doc, book_id)
    sections = db.query(Section).filter(Section.book_id == book_id).all()
    for asset in assets:
        section_id = None
        best_level = -1
        for section in sections:
            if section.page_start <= asset["page_num"] <= section.page_end:
                if section.level >= best_level:
                    best_level = section.level
                    section_id = section.id
        db.add(
            SectionAsset(
                book_id=book_id,
                section_id=section_id,
                page_num=asset["page_num"],
                file_path=asset["file_path"],
                caption=asset["caption"],
            )
        )

    existing_progress = db.query(ReadingProgress).filter(ReadingProgress.book_id == book_id).first()
    if not existing_progress:
        db.add(ReadingProgress(book_id=book_id, last_page=1, last_section_id=None))

    db.commit()
    doc.close()
    logger.info("Ingestion complete", extra={"book_id": book_id})


def save_pdf_file(book_id: int, filename: str, data: bytes) -> str:
    os.makedirs(settings.pdf_dir, exist_ok=True)
    safe_name = filename.replace(" ", "_")
    file_path = os.path.join(settings.pdf_dir, f"{book_id}_{safe_name}")
    with open(file_path, "wb") as f:
        f.write(data)
    return file_path
