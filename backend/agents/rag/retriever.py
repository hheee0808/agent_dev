"""RAG 검색 — pgvector 코사인 유사도."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.ingest.db import get_connection
from backend.ingest.embedding import embed_text

log = logging.getLogger(__name__)

DISTANCE_THRESHOLD = 0.5


@dataclass
class Chunk:
    content: str
    source: str
    page_number: int
    score: float
    chunk_id: int


def search(query: str, top_k: int = 5) -> list[Chunk]:
    embedding = embed_text(query)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT content, source, page_number,
                       1 - (embedding <=> %s::vector) AS score, id
                FROM document_chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding, embedding, top_k),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    chunks = []
    for r in rows:
        score = float(r[3])
        if score < DISTANCE_THRESHOLD:
            continue
        chunks.append(Chunk(
            content=r[0], source=r[1], page_number=r[2],
            score=score, chunk_id=r[4],
        ))

    log.info("search: query=%s top_k=%d results=%d", query[:50], top_k, len(chunks))
    return chunks
