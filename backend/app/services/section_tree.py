import re
from dataclasses import dataclass
import fitz


@dataclass
class SectionNode:
    level: int
    title: str
    page: int


def build_sections_from_toc(doc: fitz.Document) -> list[SectionNode]:
    toc = doc.get_toc(simple=True)
    sections: list[SectionNode] = []
    for entry in toc:
        if len(entry) < 3:
            continue
        level, title, page = entry[0], entry[1].strip(), entry[2]
        sections.append(SectionNode(level=level, title=title, page=page))
    return sections


def infer_sections_from_headings(doc: fitz.Document) -> list[SectionNode]:
    pattern = re.compile(r"^(chapter|CHAPTER|Chapter)\s+\d+|^\d+\.\s+|^[A-Z][A-Z\s]{8,}$")
    sections: list[SectionNode] = []
    for page_index in range(doc.page_count):
        page = doc.load_page(page_index)
        text = page.get_text("text")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines[:10]:
            if pattern.match(line):
                sections.append(SectionNode(level=1, title=line, page=page_index + 1))
                break
    if not sections:
        sections.append(SectionNode(level=1, title="Full Document", page=1))
    return sections


def compute_page_ranges(nodes: list[SectionNode], page_count: int) -> list[tuple[SectionNode, int, int]]:
    ranges: list[tuple[SectionNode, int, int]] = []
    for idx, node in enumerate(nodes):
        start = node.page
        end = page_count
        for next_node in nodes[idx + 1 :]:
            if next_node.level <= node.level:
                end = max(start, next_node.page - 1)
                break
        ranges.append((node, start, end))
    return ranges
