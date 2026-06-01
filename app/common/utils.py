import re
import uuid
from datetime import datetime


def generate_uuid() -> str:
    return str(uuid.uuid4())


def generate_filename(ext: str) -> str:
    return f"{datetime.now().strftime('%Y%m%d')}_{generate_uuid()}.{ext}"


# Mermaid diagram start keywords (outside fenced blocks = formatting bug)
_MERMAID_STARTS = {
    'graph', 'sequenceDiagram', 'classDiagram', 'flowchart',
    'gantt', 'pie', 'erDiagram', 'stateDiagram', 'gitGraph',
    'mindmap', 'timeline', 'journey', 'quadrantChart',
}


def sanitize_markdown(text: str) -> str:
    """Post-process LLM output to fix common markdown formatting issues."""
    if not text:
        return text

    lines = text.split('\n')
    out = []
    in_fence = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Track code fence boundaries
        if stripped.startswith('```'):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue

        if in_fence:
            out.append(line)
            i += 1
            continue

        # ── Fix table rows ──
        if stripped.startswith('|') and stripped.endswith('|'):
            # Collapse consecutive pipes (fix || bug)
            line = re.sub(r'\|{2,}', '|', line)
            # Remove colons in separator lines (fix |:---| -> |---|)
            if re.match(r'^[\|\s\-:]+$', stripped):
                line = re.sub(r':-+', '---', line)
                line = re.sub(r'-+:', '---', line)
                line = re.sub(r':-+:', '---', line)
            # Ensure each cell has exactly one space padding
            cells = line.split('|')
            cleaned_cells = []
            for c in cells:
                c = c.strip()
                cleaned_cells.append(f' {c} ' if c else '')
            line = '|'.join(cleaned_cells)

        # ── Fix bare mermaid diagram starts ──
        first_word = stripped.split()[0] if stripped else ''
        if first_word in _MERMAID_STARTS:
            out.append('```mermaid')
            while i < len(lines) and lines[i].strip() != '' and not lines[i].strip().startswith('```'):
                out.append(lines[i])
                i += 1
            out.append('```')
            continue

        out.append(line)
        i += 1

    text = '\n'.join(out)

    # Close any unclosed code fence
    fence_count = len(re.findall(r'(?m)^```', text))
    if fence_count % 2 != 0:
        text += '\n```'

    return text
