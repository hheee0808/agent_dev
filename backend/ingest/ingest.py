"""문서 ingest — 파일 → 청크 → 임베딩 → pgvector 저장."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from backend.ingest.chunker import chunk_text
from backend.ingest.db import get_connection
from backend.ingest.embedding import embed_texts
from backend.ingest.loader import load_document

log = logging.getLogger(__name__)

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def ingest_file(file_path: str) -> int:
    path = Path(file_path)
    file_name = path.name
    file_type = path.suffix.lower().lstrip(".")
    file_size = path.stat().st_size

    pages = load_document(file_path)
    if not pages:
        return 0

    chunks: list[tuple[str, int, str]] = []
    for page_text, page_num, page_type in pages:
        for piece in chunk_text(page_text, CHUNK_SIZE, CHUNK_OVERLAP):
            chunks.append((piece, page_num, page_type))

    if not chunks:
        return 0

    contents = [c[0] for c in chunks]
    embeddings = embed_texts(contents)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO documents (file_name, file_type, file_size) VALUES (%s, %s, %s) RETURNING id",
                (file_name, file_type, file_size),
            )
            doc_id = cur.fetchone()[0]

            for idx, ((piece, page_num, page_type), embedding) in enumerate(zip(chunks, embeddings)):
                metadata = json.dumps({"page_type": page_type, "file_type": file_type})
                cur.execute(
                    """INSERT INTO document_chunks
                       (document_id, source, chunk_index, content, embedding, page_number, metadata)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (doc_id, file_name, idx, piece, embedding, page_num, metadata),
                )
        conn.commit()
        log.info("ingested %s: %d chunks", file_name, len(chunks))
    finally:
        conn.close()

    return len(chunks)


def ingest_text(text: str, source: str = "manual") -> int:
    """raw 텍스트를 직접 ingest (URL 크롤 결과 등)."""
    chunks_text = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
    if not chunks_text:
        return 0

    embeddings = embed_texts(chunks_text)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO documents (file_name, file_type, file_size) VALUES (%s, %s, %s) RETURNING id",
                (source, "text", len(text)),
            )
            doc_id = cur.fetchone()[0]

            for idx, (piece, embedding) in enumerate(zip(chunks_text, embeddings)):
                cur.execute(
                    """INSERT INTO document_chunks
                       (document_id, source, chunk_index, content, embedding, page_number, metadata)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (doc_id, source, idx, piece, embedding, 1, "{}"),
                )
        conn.commit()
        log.info("ingested text '%s': %d chunks", source, len(chunks_text))
    finally:
        conn.close()

    return len(chunks_text)
