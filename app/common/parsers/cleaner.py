import re


def clean_parsed_text(text: str) -> str:
    """Clean parsed document text for better chunking and retrieval quality."""

    # 1. Normalize Unicode
    text = _normalize_unicode(text)

    # 2. Remove excessive whitespace
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)

    # 3. Strip trailing whitespace per line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(line for line in lines if line)

    # 4. Merge broken lines (single newlines within paragraphs)
    text = _merge_broken_lines(text)

    # 5. Remove common noise patterns
    text = _remove_noise(text)

    return text.strip()


def _normalize_unicode(text: str) -> str:
    """Normalize Unicode characters to standard forms."""
    import unicodedata
    # Normalize to NFC form (composed characters)
    text = unicodedata.normalize("NFC", text)
    # Replace common Unicode artifacts
    replacements = {
        '–': '-',   # en dash
        '—': '--',  # em dash
        '‘': "'",   # left single quote
        '’': "'",   # right single quote
        '“': '"',   # left double quote
        '”': '"',   # right double quote
        '…': '...',  # ellipsis
        ' ': ' ',   # non-breaking space
        '　': ' ',   # full-width space (Chinese)
        '，': ',',   # full-width comma
        '．': '.',   # full-width period
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _merge_broken_lines(text: str) -> str:
    """Merge single newlines that are within the same paragraph (not between paragraphs)."""
    paragraphs = text.split("\n\n")
    merged = []
    for para in paragraphs:
        lines = para.split("\n")
        if len(lines) <= 1:
            merged.append(para)
            continue

        # Merge lines that look like continuation (don't start with markdown markers or special chars)
        result = [lines[0]]
        for line in lines[1:]:
            stripped = line.strip()
            if not stripped:
                continue
            # Lines that start new semantic units - don't merge
            if re.match(r'^[#>-]|\d+[\.\)、]|[一二三四五六七八九十]+[、\.]|[\(（]\d+[\)）]', stripped):
                result.append(line)
            elif re.match(r'^[•‣◦○●]', stripped):
                result.append(line)
            elif stripped.startswith('|'):  # Table row
                result.append(line)
            elif result and len(result[-1]) < 60:
                # Short previous line - likely a heading, keep separate
                result.append(line)
            else:
                # Merge continuation line
                result[-1] = result[-1] + stripped
        merged.append("\n".join(result))

    return "\n\n".join(merged)


def _remove_noise(text: str) -> str:
    """Remove common noise patterns from extracted text."""
    # Remove page numbers (standalone digits at start/end of lines)
    text = re.sub(r'^\d{1,4}\s*$', '', text, flags=re.MULTILINE)
    # Remove lines that are purely punctuation
    text = re.sub(r'^[\.\-=_*#~]{3,}\s*$', '', text, flags=re.MULTILINE)
    # Remove common header/footer artifacts
    text = re.sub(r'^\s*Confidential\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'^\s*All Rights Reserved\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    # Remove "第X页/共Y页" patterns
    text = re.sub(r'第\s*\d+\s*页\s*/\s*共\s*\d+\s*页', '', text)

    return text


def extract_structure_metadata(text: str) -> dict:
    """Extract document structure metadata for better chunk context.

    Returns a dict with:
    - sections: list of (heading, content) tuples
    - key_terms: list of important-looking terms
    - definitions: list of definition-like sentences
    """
    sections = []
    current_heading = ""
    current_content = []

    for line in text.split("\n"):
        markdown_heading = re.match(r'^#{1,4}\s+', line)
        chinese_heading = re.match(
            r'^(第[一二三四五六七八九十百\d]+[章节篇部]|[一二三四五六七八九十百\d]+[、.．]\s*)\S+',
            line,
        )
        if markdown_heading or chinese_heading:
            if current_content:
                sections.append({"heading": current_heading, "content": "\n".join(current_content)})
                current_content = []
            current_heading = re.sub(r'^#{1,4}\s+', '', line).strip()
        else:
            current_content.append(line)

    if current_content:
        sections.append({"heading": current_heading, "content": "\n".join(current_content)})

    # Extract definitions (sentences containing "是指", "定义为", "is defined as", etc.)
    def_patterns = [
        r'[^。]*是指[^。]*。',
        r'[^。]*定义为[^。]*。',
        r'[^。]*指的是[^。]*。',
        r'[^.]*is defined as[^.]*\.',
        r'[^.]*refers to[^.]*\.',
    ]
    definitions = []
    for pattern in def_patterns:
        definitions.extend(re.findall(pattern, text, re.IGNORECASE))

    return {
        "sections": sections,
        "definitions": definitions[:20],
    }
