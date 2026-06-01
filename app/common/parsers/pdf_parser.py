import re

try:
    import pdfplumber
    _pdfplumber_available = True
except ImportError:
    pdfplumber = None
    _pdfplumber_available = False


def parse_pdf(file_path: str) -> str:
    """Parse PDF with table extraction, page tracking, and layout-aware cleaning."""
    if not _pdfplumber_available:
        raise ImportError("pdfplumber is not installed. Install it with: pip install pdfplumber")

    pages_output = []
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            page_parts = []

            # ── Extract tables first (before text to avoid duplication) ──
            tables = page.extract_tables()
            table_regions = []
            if tables:
                for table in tables:
                    if not table or len(table) < 1:
                        continue
                    table_md = _table_to_markdown(table)
                    if table_md:
                        page_parts.append(table_md)
                        # Track table regions to remove duplicated text
                        table_regions.append(_estimate_table_bbox(table))

            # ── Extract text ──
            text = page.extract_text(layout=True, x_tolerance=2, y_tolerance=2)
            if text and text.strip():
                cleaned = _clean_page_text(text.strip(), table_regions)
                if cleaned:
                    page_parts.append(cleaned)

            if page_parts:
                pages_output.append(f"## 第{page_num}页\n\n" + "\n\n".join(page_parts))

    return "\n\n".join(pages_output)


def _table_to_markdown(table: list) -> str:
    """Convert a table (list of rows) to markdown format."""
    if not table:
        return ""

    cleaned_rows = []
    for row in table:
        if row and any(cell for cell in row if cell and str(cell).strip()):
            cleaned_cells = [str(cell).strip().replace("\n", " ") if cell else "" for cell in row]
            cleaned_rows.append(cleaned_cells)

    if not cleaned_rows:
        return ""

    # Determine column count from the widest row
    max_cols = max(len(row) for row in cleaned_rows)
    # Normalize all rows to same width
    for row in cleaned_rows:
        while len(row) < max_cols:
            row.append("")

    lines = []
    # Header row
    lines.append("| " + " | ".join(cleaned_rows[0]) + " |")
    # Separator
    lines.append("| " + " | ".join(["---"] * max_cols) + " |")
    # Data rows
    for row in cleaned_rows[1:]:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def _estimate_table_bbox(table: list) -> dict:
    """Estimate bounding box of a table region for text dedup. Simplified placeholder."""
    return {"x0": 0, "x1": 1000, "top": 0, "bottom": 1000}


def _clean_page_text(text: str, table_regions: list = None) -> str:
    """Clean extracted page text: remove noise, fix layout artifacts."""
    # Remove excessive blank lines
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    # Remove lines that are just page numbers or headers/footers
    text = re.sub(r"^\d{1,4}\s*$", "", text, flags=re.MULTILINE)
    # Collapse multiple spaces (but not newlines)
    text = re.sub(r"[ ]{2,}", " ", text)
    # Remove leading/trailing whitespace per line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(line for line in lines if line)
    return text
