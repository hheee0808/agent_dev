"""임베딩 모듈 — Gemini embedding API."""

from __future__ import annotations

from google.genai import types

from backend.common.llm import get_client

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768
EMBED_BATCH_MAX = 100


def embed_text(text: str) -> list[float]:
    result = get_client().models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
    )
    return result.embeddings[0].values


def embed_texts(texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    client = get_client()
    for i in range(0, len(texts), EMBED_BATCH_MAX):
        batch = list(texts[i:i + EMBED_BATCH_MAX])
        if not batch:
            continue
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=batch,
            config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
        )
        out.extend(e.values for e in result.embeddings)
    return out
