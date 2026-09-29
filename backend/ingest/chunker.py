"""텍스트 청킹 — 문장/단락 경계 우선 분할."""

from __future__ import annotations

_BREAKS = (
    "\n\n", "\n",
    "다. ", "요. ", "음. ", "임. ",
    ". ", "! ", "? ",
    ", ",
)


def _find_break(text: str, start: int, end: int) -> int:
    window_start = max(start, end - 200)
    for sep in _BREAKS:
        idx = text.rfind(sep, window_start, end)
        if idx != -1:
            return idx + len(sep)
    return end


def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        if end < n:
            end = _find_break(text, start, end)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        start = max(end - chunk_overlap, start + 1)
    return chunks
