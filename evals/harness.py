"""Eval harness — 에이전트별 평가 케이스 실행 + 점수 산출."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from backend.common.llm import generate

log = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = """\
You are an evaluation judge. Score the agent's response on these criteria:
- relevance (0-10): Does it answer the question?
- accuracy (0-10): Are the facts correct?
- completeness (0-10): Does it cover all aspects?
- citation (0-10): Are sources properly cited? (skip if N/A, return -1)

Return JSON: {"relevance": 8, "accuracy": 7, "completeness": 6, "citation": 9, "notes": "..."}
"""


@dataclass
class EvalCase:
    agent: str
    input: dict
    expected_keywords: list[str] = field(default_factory=list)
    expected_agent: str = ""
    description: str = ""


@dataclass
class EvalResult:
    case: EvalCase
    output: str
    scores: dict = field(default_factory=dict)
    elapsed_s: float = 0.0
    error: str | None = None
    routed_to: str = ""


def load_cases(path: str) -> list[EvalCase]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [EvalCase(**c) for c in data]


async def run_eval(cases: list[EvalCase], supervisor) -> list[EvalResult]:
    results = []
    for case in cases:
        t0 = time.time()
        try:
            result = await supervisor.handle(case.input.get("message", ""), trigger="eval")
            output = str(result.output) if result.output else ""
            elapsed = time.time() - t0

            scores = _judge(case, output)

            keyword_hits = sum(1 for kw in case.expected_keywords if kw.lower() in output.lower())
            if case.expected_keywords:
                scores["keyword_recall"] = keyword_hits / len(case.expected_keywords)

            if case.expected_agent:
                scores["routing_correct"] = 1.0 if result.agent == case.expected_agent else 0.0

            results.append(EvalResult(
                case=case, output=output[:1000], scores=scores,
                elapsed_s=elapsed, routed_to=result.agent,
            ))
        except Exception as e:
            results.append(EvalResult(
                case=case, output="", elapsed_s=time.time() - t0, error=str(e),
            ))

    return results


def _judge(case: EvalCase, output: str) -> dict:
    prompt = (
        f"Question: {case.input.get('message', '')}\n"
        f"Agent response:\n{output[:2000]}"
    )
    text, _ = generate(prompt, system_instruction=JUDGE_SYSTEM_PROMPT, response_mime_type="application/json")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"judge_error": text[:200]}


def summary(results: list[EvalResult]) -> dict:
    if not results:
        return {}

    total_scores: dict[str, list[float]] = {}
    for r in results:
        for k, v in r.scores.items():
            if isinstance(v, (int, float)) and v >= 0:
                total_scores.setdefault(k, []).append(v)

    avg = {k: round(sum(v) / len(v), 2) for k, v in total_scores.items()}
    avg["total_cases"] = len(results)
    avg["errors"] = sum(1 for r in results if r.error)
    avg["avg_latency_s"] = round(sum(r.elapsed_s for r in results) / len(results), 2)
    return avg
