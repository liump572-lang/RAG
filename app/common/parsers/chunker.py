import re
from typing import List


def recursive_character_split(
    text: str,
    chunk_size: int = 1024,
    chunk_overlap: int = 200,
) -> List[str]:
    """Split text into chunks at natural boundaries, safe for Chinese text."""
    if not text:
        return []

    separators = ["\n\n", "\n", "。", "；", "，", " ", ""]
    return _split_text(text, separators, chunk_size, chunk_overlap)


def _split_text(
    text: str,
    separators: List[str],
    chunk_size: int,
    chunk_overlap: int,
) -> List[str]:
    final_chunks = []
    separator = separators[0]
    remaining_seps = separators[1:] if len(separators) > 1 else []

    if not separator:
        # Last resort: character-level split, ensure no mid-char breaks
        return _char_split_safe(text, chunk_size, chunk_overlap)

    splits = [s.strip() for s in text.split(separator) if s.strip()]

    good_splits = []
    for s in splits:
        if len(s) <= chunk_size:
            good_splits.append(s)
        else:
            # Flush accumulated good splits first
            if good_splits:
                merged = _merge_splits(good_splits, separator, chunk_size, chunk_overlap)
                final_chunks.extend(merged)
                good_splits = []

            # Try remaining separators on this oversized split
            if remaining_seps:
                sub_chunks = _split_text(s, remaining_seps, chunk_size, chunk_overlap)
                final_chunks.extend(sub_chunks)
            else:
                # Last resort: safe char split
                sub_chunks = _char_split_safe(s, chunk_size, chunk_overlap)
                final_chunks.extend(sub_chunks)

    if good_splits:
        merged = _merge_splits(good_splits, separator, chunk_size, chunk_overlap)
        final_chunks.extend(merged)

    return _deduplicate_overlap(final_chunks)


def _char_split_safe(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Split text character by character, ensuring no multi-byte char is broken."""
    chunks = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + chunk_size, n)
        # Ensure we don't break in the middle of a multi-byte UTF-8 char
        # or a Unicode surrogate pair
        while end < n:
            ch = text[end]
            # Check if we're in the middle of a surrogate pair (emoji etc.)
            if '\uDC00' <= ch <= '\uDFFF':
                end -= 1
            else:
                break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= n:
            break

        # Move start back by overlap amount, but not past the end
        start = max(start, end - chunk_overlap)

    return chunks


def _merge_splits(
    splits: List[str],
    separator: str,
    chunk_size: int,
    chunk_overlap: int,
) -> List[str]:
    chunks = []
    current = []
    current_len = 0

    for s in splits:
        sep_len = len(separator) if current else 0
        if current_len + sep_len + len(s) > chunk_size and current:
            chunks.append(separator.join(current))

            # Build overlap window from the end of current chunks
            overlap_len = 0
            overlap_splits = []
            for rs in reversed(current):
                next_len = overlap_len + len(rs) + (len(separator) if overlap_len else 0)
                if next_len > chunk_overlap:
                    break
                overlap_splits.insert(0, rs)
                overlap_len = next_len

            current = overlap_splits
            current_len = overlap_len

        current.append(s)
        current_len += sep_len + len(s)

    if current:
        chunks.append(separator.join(current))

    return chunks


def _deduplicate_overlap(chunks: List[str]) -> List[str]:
    """Remove exact duplicate consecutive chunks and trim excessive overlap."""
    if len(chunks) < 2:
        return chunks

    result = [chunks[0]]
    for c in chunks[1:]:
        prev = result[-1]

        # Check if c is a complete substring of prev
        if c in prev:
            continue
        # Check if prev is a complete substring of c
        if prev in c and len(prev) < len(c):
            result[-1] = c
            continue

        # Trim overlapping suffix from prev (up to chunk_overlap/2)
        max_check = min(len(prev), len(c), 100)
        overlap_len = 0
        for i in range(max_check, 0, -1):
            if prev[-i:] == c[:i]:
                overlap_len = i
                break

        if overlap_len > 0:
            result[-1] = prev[:-overlap_len]

        result.append(c)

    return result
