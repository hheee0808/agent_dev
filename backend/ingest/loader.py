"""파일 로더 — 확장자별 텍스트 추출."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)

Page = tuple[str, int, str]  # (text, page_number, page_type)

_KO_ENCODINGS = ("utf-8", "cp949", "euc-kr", "utf-16")


def _read_text_fallback(path: str) -> str:
    for enc in _KO_ENCODINGS:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _load_txt(path: str) -> list[Page]:
    text = _read_text_fallback(path).strip()
    return [(text, 1, "text")] if text else []


def _load_md(path: str) -> list[Page]:
    return _load_txt(path)


def _load_pdf(path: str) -> list[Page]:
    from pypdf import PdfReader
    reader = PdfReader(path)
    out: list[Page] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            out.append((text, i, "text"))
    return out


def _load_docx(path: str) -> list[Page]:
    from docx import Document
    doc = Document(path)
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip()).strip()
    return [(text, 1, "text")] if text else []


LOADERS: dict[str, Callable[[str], list[Page]]] = {
    ".pdf": _load_pdf,
    ".txt": _load_txt,
    ".md": _load_md,
    ".docx": _load_docx,
}


def load_document(path: str) -> list[Page]:
    ext = Path(path).suffix.lower()
    loader = LOADERS.get(ext)
    if not loader:
        raise ValueError(f"지원하지 않는 확장자: {ext}")
    return loader(path)
