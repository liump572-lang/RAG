import re
from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn


def parse_docx(file_path: str) -> str:
    """Parse DOCX with heading hierarchy, structure preservation, and table extraction."""
    doc = Document(file_path)

    # Build heading style set
    heading_styles = _get_heading_styles(doc)

    sections = []
    current_section = {"heading": "", "level": 0, "parts": []}

    # Process all body elements in order (paragraphs + tables interleaved)
    for element in _iter_body_elements(doc):
        if element["type"] == "paragraph":
            para = element["element"]
            text = para.text.strip()
            if not text:
                continue

            para_style = para.style.name if para.style else ""
            heading_level = _detect_heading_level(para_style, heading_styles, text)

            if heading_level > 0:
                # Flush current section
                if current_section["parts"] or current_section["heading"]:
                    sections.append(_build_section(current_section))
                current_section = {"heading": text, "level": heading_level, "parts": []}
            else:
                # Check if it's a list item
                is_list = _is_list_paragraph(para)
                prefix = "  " if is_list else ""
                current_section["parts"].append(prefix + text)

        elif element["type"] == "table":
            table_md = _docx_table_to_markdown(element["element"])
            if table_md:
                current_section["parts"].append(table_md)

    # Flush last section
    if current_section["parts"] or current_section["heading"]:
        sections.append(_build_section(current_section))

    if not sections:
        return ""

    return "\n\n".join(sections)


def _get_heading_styles(doc) -> set:
    """Collect all paragraph style names that represent headings."""
    heading_styles = set()
    for style in doc.styles:
        if style.type == WD_STYLE_TYPE.PARAGRAPH:
            name = style.name.lower() if style.name else ""
            if "heading" in name or name in {"title", "subtitle", "标题", "副标题"}:
                heading_styles.add(style.name)
    return heading_styles


def _detect_heading_level(style_name: str, heading_styles: set, text: str) -> int:
    """Detect heading level from style. Returns 0 if not a heading."""
    if not style_name:
        return 0

    name_lower = style_name.lower()

    # Built-in heading styles
    if "heading 1" in name_lower or name_lower == "title":
        return 1
    if "heading 2" in name_lower:
        return 2
    if "heading 3" in name_lower or name_lower == "subtitle":
        return 3
    if style_name in heading_styles:
        return 2

    # Heuristic: short text, all bold, starts with "第.*章" or "第.*节"
    if len(text) <= 40 and re.match(r"^(第[一二三四五六七八九十\d]+[章节]|[一二三四五六七八九十\d]+[\.、\)）])", text):
        return 2

    return 0


def _is_list_paragraph(para) -> bool:
    """Check if a paragraph is a list item (ordered or unordered)."""
    if para.style and para.style.name:
        name = para.style.name.lower()
        if "list" in name:
            return True

    # Check numbering property
    numPr = para._element.find(qn('w:pPr'))
    if numPr is not None:
        numPrElem = numPr.find(qn('w:numPr'))
        if numPrElem is not None:
            return True

    # Check text pattern: starts with bullet or number
    text = para.text.strip()
    if re.match(r'^[•‣◦○●\-•]\s', text):
        return True
    if re.match(r'^\d+[\.\)、]\s', text):
        return True
    if re.match(r'^[\(（]\d+[\)）]\s', text):
        return True

    return False


def _build_section(section: dict) -> str:
    """Build a markdown-formatted section from heading and parts."""
    heading = section["heading"]
    level = section["level"]
    parts = section["parts"]

    if not heading and not parts:
        return ""

    result = ""
    if heading:
        prefix = "#" * min(level, 4)
        result += f"{prefix} {heading}\n\n"

    if parts:
        result += "\n\n".join(parts)

    return result


def _docx_table_to_markdown(table) -> str:
    """Convert a DOCX table to markdown format."""
    rows = []
    for row in table.rows:
        cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        if any(cells):
            rows.append(cells)

    if not rows:
        return ""

    max_cols = max(len(row) for row in rows)
    for row in rows:
        while len(row) < max_cols:
            row.append("")

    lines = []
    lines.append("| " + " | ".join(rows[0]) + " |")
    lines.append("| " + " | ".join(["---"] * max_cols) + " |")
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def _iter_body_elements(doc):
    """
    Iterate through body elements (paragraphs and tables) in document order.
    This preserves interleaving of paragraphs and tables.
    """
    body = doc.element.body
    para_elements = {p._element: p for p in doc.paragraphs}
    table_elements = {t._element: t for t in doc.tables}

    for child in body:
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if tag == 'p' and child in para_elements:
            yield {"type": "paragraph", "element": para_elements[child]}
        elif tag == 'tbl' and child in table_elements:
            yield {"type": "table", "element": table_elements[child]}
