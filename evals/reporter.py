"""Eval 결과 리포터 — 콘솔 + Langfuse."""

from __future__ import annotations

import json
import logging

from backend.common.trace import get_langfuse
from evals.harness import EvalResult

log = logging.getLogger(__name__)


def print_report(results: list[EvalResult], summary: dict) -> None:
    print("\n" + "=" * 60)
    print("EVAL RESULTS")
    print("=" * 60)

    for r in results:
        status = "ERROR" if r.error else "OK"
        desc = r.case.description or r.case.agent
        scores_str = " ".join(f"{k}={v}" for k, v in r.scores.items() if isinstance(v, (int, float)))
        print(f"  [{status}] {desc:40s} routed={r.routed_to:12s} {scores_str} ({r.elapsed_s:.1f}s)")

    print("-" * 60)
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print("=" * 60)


def report_to_langfuse(results: list[EvalResult], summary: dict) -> None:
    lf = get_langfuse()
    if lf is None:
        log.info("Langfuse 미설정 — eval 결과는 콘솔만 출력")
        return

    try:
        for r in results:
            trace = lf.trace(
                name=f"eval.{r.case.agent}",
                input=r.case.input,
                output={"text": r.output[:500]},
                metadata={
                    "description": r.case.description,
                    "routed_to": r.routed_to,
                    "elapsed_s": r.elapsed_s,
                    "error": r.error,
                },
                tags=["eval", r.case.agent],
            )
            for k, v in r.scores.items():
                if isinstance(v, (int, float)) and v >= 0:
                    trace.score(name=k, value=float(v))

        log.info("eval results pushed to Langfuse: %d traces", len(results))
    except Exception as e:
        log.warning("Langfuse eval report failed: %s", e)
