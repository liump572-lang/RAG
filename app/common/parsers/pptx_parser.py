import re
from pptx import Presentation
from pptx.shapes.placeholder import PlaceholderPicture


def parse_pptx(file_path: str) -> str:
    """Parse PPTX with slide titles, body text, notes, and table extraction."""
    prs = Presentation(file_path)
    slides_output = []

    for slide_num, slide in enumerate(prs.slides, 1):
        title_texts = []
        body_texts = []
        table_texts = []
        notes_text = ""

        for shape in slide.shapes:
            if shape.has_table:
                table_md = _pptx_table_to_markdown(shape.table)
                if table_md:
                    table_texts.append(table_md)
                continue

            if not shape.has_text_frame:
                continue

            shape_text = _extract_shape_text(shape)
            if not shape_text:
                continue

            is_title = _is_title_shape(shape)
            if is_title:
                title_texts.append(shape_text)
            else:
                body_texts.append(shape_text)

        # Extract slide notes
        if slide.has_notes_slide and slide.notes_slide:
            notes_tf = slide.notes_slide.notes_text_frame
            if notes_tf:
                notes_text = notes_tf.text.strip()

        # Build slide output
        slide_parts = []
        slide_header = f"## 幻灯片{slide_num}"

        if title_texts:
            slide_header += f"：{'；'.join(title_texts)}"

        slide_parts.append(slide_header)

        if body_texts:
            slide_parts.append("\n\n".join(body_texts))

        if table_texts:
            slide_parts.append("\n\n".join(table_texts))

        if notes_text:
            slide_parts.append(f"> **讲稿备注**：{notes_text}")

        slides_output.append("\n\n".join(slide_parts))

    return "\n\n---\n\n".join(slides_output)


def _is_title_shape(shape) -> bool:
    """Check if a shape is a title placeholder."""
    # Check if it's a title or subtitle placeholder
    try:
        placeholder = shape.placeholder_format
        if placeholder and placeholder.type is not None:
            ph_type = str(placeholder.type)
            if "TITLE" in ph_type.upper() or "CENTER" in ph_type.upper():
                return True
    except Exception:
        pass

    # Heuristic: short text, large font, at top of slide
    if shape.has_text_frame:
        text = shape.text_frame.text.strip()
        if len(text) <= 80:
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    if run.font.size and run.font.size >= 24 * 12700:  # 24pt or larger
                        return True
                    if run.font.bold:
                        return True

    return False


def _extract_shape_text(shape) -> str:
    """Extract text from a shape, preserving paragraph structure."""
    paragraphs = []
    for para in shape.text_frame.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # Detect list level from indentation
        level = para.level if para.level is not None else 0
        indent = "  " * level
        if level > 0:
            paragraphs.append(indent + "- " + text)
        else:
            paragraphs.append(text)

    if not paragraphs:
        return ""

    return "\n".join(paragraphs)


def _pptx_table_to_markdown(table) -> str:
    """Convert a PPTX table to markdown."""
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
