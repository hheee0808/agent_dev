"""Gemini 기반 관련성 필터 + 랭킹."""

from __future__ import annotations

import json
import logging

from backend.agents.curator.sources import Article
from backend.common.llm import generate

log = logging.getLogger(__name__)

RANK_SYSTEM_PROMPT = """\
You are a content curator for an AI agent developer.
Your user is interested in: AI agents, LLM APIs (Anthropic, OpenAI, Google Gemini), \
MCP (Model Context Protocol), agent architectures (ReAct, tool-use, multi-agent), \
RAG, vector databases, and practical AI engineering.

Given a list of articles (title + source + optional summary), score each 1-10 for relevance.
Return JSON array: [{"index": 0, "score": 8, "reason": "..."}, ...]
Only include items scoring 6 or above.
"""


async def rank_articles(articles: list[Article], top_k: int = 15) -> list[Article]:
    if not articles:
        return []

    items = []
    for i, a in enumerate(articles):
        entry = f"[{i}] ({a.source}) {a.title}"
        if a.summary:
            entry += f" — {a.summary[:150]}"
        items.append(entry)

    prompt = "Rate these articles:\n\n" + "\n".join(items)

    text, usage = generate(
        prompt,
        system_instruction=RANK_SYSTEM_PROMPT,
        response_mime_type="application/json",
    )

    try:
        scored = json.loads(text)
    except json.JSONDecodeError:
        log.warning("ranker JSON parse failed, returning top by source score")
        return sorted(articles, key=lambda a: a.score, reverse=True)[:top_k]

    scored.sort(key=lambda x: x.get("score", 0), reverse=True)
    ranked = []
    for item in scored[:top_k]:
        idx = item.get("index", -1)
        if 0 <= idx < len(articles):
            a = articles[idx]
            a.summary = item.get("reason", a.summary)
            ranked.append(a)

    log.info("ranked: %d/%d articles passed filter", len(ranked), len(articles))
    return ranked
