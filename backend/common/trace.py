"""실행 추적 — Langfuse 연동 + 자체 로그."""

from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)

_langfuse = None
_disabled = False


def get_langfuse():
    global _langfuse, _disabled
    if _disabled:
        return None
    if _langfuse is not None:
        return _langfuse

    secret = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
    public = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
    if not secret or not public:
        _disabled = True
        log.info("Langfuse 키 미설정 → 비활성")
        return None

    try:
        from langfuse import Langfuse
        _langfuse = Langfuse(
            secret_key=secret,
            public_key=public,
            host=os.getenv("LANGFUSE_HOST", "http://localhost:3001"),
        )
        log.info("Langfuse 활성: host=%s", os.getenv("LANGFUSE_HOST"))
        return _langfuse
    except Exception as e:
        log.warning("Langfuse 초기화 실패: %s", e)
        _disabled = True
        return None


def trace_run(
    *,
    agent_name: str,
    trigger: str,
    input_payload: dict,
    output_payload: dict,
    elapsed_s: float | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    cost_usd: float | None = None,
    model: str | None = None,
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    log.info(
        "trace: agent=%s trigger=%s elapsed=%.1fs tokens=%s/%s cost=$%.6f error=%s",
        agent_name, trigger, elapsed_s or 0,
        prompt_tokens, completion_tokens, cost_usd or 0, error,
    )

    lf = get_langfuse()
    if lf is None:
        return

    try:
        trace = lf.trace(
            name=f"{agent_name}.{trigger}",
            input=input_payload,
            output=output_payload,
            metadata=metadata or {},
            tags=[agent_name, trigger],
            release=os.getenv("APP_ENV", "dev"),
        )
        if prompt_tokens is not None or completion_tokens is not None:
            trace.generation(
                name=f"{agent_name}.model",
                model=model,
                usage={
                    "input": prompt_tokens or 0,
                    "output": completion_tokens or 0,
                    "total": (prompt_tokens or 0) + (completion_tokens or 0),
                    "unit": "TOKENS",
                    "total_cost": cost_usd or 0.0,
                },
            )
        if error:
            trace.update(level="ERROR", status_message=error[:500])
    except Exception as e:
        log.debug("Langfuse trace 실패: %s", e)
