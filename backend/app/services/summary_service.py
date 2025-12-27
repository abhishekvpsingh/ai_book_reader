import logging
from typing import Iterable
import fitz
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import Book, Section, Summary, SummaryVersion, SectionAsset
from app.services.llm_providers import get_provider

logger = logging.getLogger(__name__)

SUMMARY_TEMPLATE = """You are an assistant summarizing a book section strictly from the provided text. Do not invent details.
Write in a friendly, conversational tone as if explaining to a student with very basic knowledge.
Avoid phrases like \"this chapter\". Instead use the section title or say \"this topic\".
Use short sentences suitable for TTS.
Use this exact template with headings (no markdown symbols, just plain text headings):
Overview
Key Concepts
Important Formulas / Code
Diagrams / Visual Explanation
Practical Notes
Key Takeaways
Figures
"""


def _collect_descendants(section: Section) -> list[Section]:
    nodes = [section]
    result = []
    while nodes:
        node = nodes.pop(0)
        result.append(node)
        nodes.extend(node.children)
    return result


def _extract_text(book_path: str, page_ranges: Iterable[tuple[int, int]]) -> str:
    doc = fitz.open(book_path)
    parts = []
    for start, end in page_ranges:
        for page_index in range(start - 1, end):
            page = doc.load_page(page_index)
            parts.append(page.get_text("text"))
    doc.close()
    return "\n".join(parts)


def _collect_image_context(db: Session, section_ids: list[int]) -> str:
    assets = (
        db.query(SectionAsset)
        .filter(SectionAsset.section_id.in_(section_ids))
        .order_by(SectionAsset.page_num)
        .all()
    )
    if not assets:
        return "No figures extracted for this section."
    lines = [f"Page {asset.page_num}: {asset.caption}" for asset in assets]
    return "\n".join(lines)


def generate_summary(db: Session, section_id: int, recursive: bool) -> tuple[SummaryVersion | None, str | None, str | None]:
    section = db.get(Section, section_id)
    if not section:
        raise ValueError("Section not found")
    book = db.get(Book, section.book_id)
    if not book:
        raise ValueError("Book not found")

    target_sections = _collect_descendants(section) if recursive else [section]
    page_ranges = [(sec.page_start, sec.page_end) for sec in target_sections]
    text = _extract_text(book.file_path, page_ranges)

    if len(text) > settings.large_content_threshold:
        warning = (
            "Section text is large. Consider summarizing at a smaller subtopic level for higher fidelity."
        )
        provider = get_provider()
        overview_prompt = (
            "You are allowed to provide a high-level overview from your own knowledge. "
            "Clearly label it as NOT derived from the book content."
        )
        overview = provider.generate(overview_prompt, section.title)
        return None, warning, (
            "This overview is generated from the model's knowledge, not directly from the book.\n\n" + overview
        )
    if len(text) > settings.max_summary_chars:
        text = text[: settings.max_summary_chars]

    image_context = _collect_image_context(db, [sec.id for sec in target_sections])
    prompt = SUMMARY_TEMPLATE
    context = (
        f"Section Title: {section.title}\n\n"
        f"Extracted Text:\n{text}\n\n"
        f"Figures referenced in this section:\n{image_context}"
    )
    provider = get_provider()
    content = provider.generate(prompt, context)

    summary = db.query(Summary).filter(Summary.section_id == section_id).first()
    if not summary:
        summary = Summary(section_id=section_id)
        db.add(summary)
        db.flush()

    latest_version = (
        db.query(SummaryVersion)
        .filter(SummaryVersion.summary_id == summary.id)
        .order_by(SummaryVersion.version_number.desc())
        .first()
    )
    next_version = 1 if not latest_version else latest_version.version_number + 1
    version = SummaryVersion(summary_id=summary.id, version_number=next_version, content=content)
    db.add(version)
    db.commit()
    db.refresh(version)

    return version, None, None
