"""리서치 플래너 — 질문을 sub-question으로 분해."""

from __future__ import annotations

import json
import logging

from backend.common.llm import generate

log = logging.getLogger(__name__)

PLANNER_PROMPT = """\
You are a research planner. Given a research question, decompose it into 3-5 specific sub-questions
that can each be independently searched and answered.

Return JSON array of strings: ["sub-question 1", "sub-question 2", ...]

Rules:
- Each sub-question should be self-contained and searchable
- Cover different angles of the main question
- Order from most fundamental to most specific
"""


def decompose(question: str) -> list[str]:
    text, _ = generate(
        f"Research question: {question}",
        system_instruction=PLANNER_PROMPT,
        response_mime_type="application/json",
    )
    try:
        subs = json.loads(text)
        if isinstance(subs, list) and all(isinstance(s, str) for s in subs):
            log.info("decomposed into %d sub-questions", len(subs))
            return subs
    except json.JSONDecodeError:
        pass

    log.warning("planner parse failed, using original question")
    return [question]
