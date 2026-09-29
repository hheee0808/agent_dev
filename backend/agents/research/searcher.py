"""웹 검색 + RAG 병렬 소스 오케스트레이션."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import httpx

from backend.agents.rag.retriever import search as rag_search
from backend.common.llm import generate

log = logging.getLogger(__name__)


@dataclass
class SearchResult:
    query: str
    snippets: list[str]
    sources: list[str]


async def web_search(query: str, max_results: int = 5) -> SearchResult:
    """HN Algolia 검색 (무료, API 키 불필요)."""
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            r = await c.get(
                "https://hn.algolia.com/api/v1/search",
                params={"query": query, "hitsPerPage": max_results, "tags": "story"},
            )
            hits = r.json().get("hits", [])
            snippets = []
            sources = []
            for h in hits:
                title = h.get("title", "")
                url = h.get("url", f"https://news.ycombinator.com/item?id={h.get('objectID', '')}")
                snippets.append(title)
                sources.append(url)
            return SearchResult(query=query, snippets=snippets, sources=sources)
        except Exception as e:
            log.warning("web search failed: %s", e)
            return SearchResult(query=query, snippets=[], sources=[])


async def rag_local_search(query: str, top_k: int = 3) -> SearchResult:
    """로컬 RAG 벡터 검색."""
    try:
        chunks = rag_search(query, top_k=top_k)
        return SearchResult(
            query=query,
            snippets=[c.content[:300] for c in chunks],
            sources=[f"{c.source}:p{c.page_number}" for c in chunks],
        )
    except Exception as e:
        log.warning("RAG search failed: %s", e)
        return SearchResult(query=query, snippets=[], sources=[])


async def search_all(query: str) -> list[SearchResult]:
    """웹 + RAG 병렬 검색."""
    results = await asyncio.gather(
        web_search(query),
        rag_local_search(query),
        return_exceptions=True,
    )
    valid = [r for r in results if isinstance(r, SearchResult) and r.snippets]
    return valid
