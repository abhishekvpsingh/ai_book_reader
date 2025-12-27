from app.models import Section


def build_tree(sections: list[Section]) -> list[dict]:
    nodes = {section.id: {"id": section.id, "title": section.title, "level": section.level, "page_start": section.page_start, "page_end": section.page_end, "children": []} for section in sections}
    roots = []
    for section in sections:
        node = nodes[section.id]
        if section.parent_id and section.parent_id in nodes:
            nodes[section.parent_id]["children"].append(node)
        else:
            roots.append(node)
    return roots
