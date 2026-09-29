import asyncio
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from functools import lru_cache

from google import genai
from google.genai import types
from google.genai.errors import ServerError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential_jitter,
)

log = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"
RETRY_CODES = (429, 500, 503)
MAX_RETRY = 15
MAX_TOTAL_SECONDS = 240

PRICING_PER_M: dict[str, tuple[float, float]] = {
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.5-pro": (1.25, 10.00),
}


@lru_cache(maxsize=1)
def get_client() -> genai.Client:
    return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def resolve_model(model: str | None = None) -> str:
    forced = os.getenv("AI_FORCE_MODEL", "").strip()
    if forced:
        return forced
    return model or os.getenv("AI_MODEL", DEFAULT_MODEL)


def cost_for(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    in_per_m, out_per_m = PRICING_PER_M.get(model, PRICING_PER_M["gemini-2.5-flash"])
    return (prompt_tokens * in_per_m + completion_tokens * out_per_m) / 1_000_000


# ── Error helpers ──────────────────────────────────────────────


class QuotaDepletedError(Exception):
    pass


def is_quota_depleted(exc: Exception) -> bool:
    s = str(exc)
    if "429" not in s and "RESOURCE_EXHAUSTED" not in s:
        return False
    return "prepayment credits depleted" in s or "billing" in s.lower()


def is_overloaded(exc: Exception) -> bool:
    if is_quota_depleted(exc):
        return False
    if isinstance(exc, ServerError):
        return exc.code in RETRY_CODES
    s = str(exc)
    return "503" in s or "UNAVAILABLE" in s


def error_message(exc: Exception) -> str:
    s = str(exc)
    if "429" in s or "RESOURCE_EXHAUSTED" in s:
        if is_quota_depleted(exc):
            return "AI 크레딧이 소진됐습니다. 결제 정보를 확인해주세요."
        return "AI 요청이 너무 많습니다. 잠시 후 다시 시도해주세요."
    if "503" in s or "UNAVAILABLE" in s:
        return "AI 서버가 잠시 바쁩니다. 잠시 후 다시 시도해주세요."
    if "500" in s:
        return "AI 서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
    return f"오류가 발생했습니다: {type(exc).__name__}: {str(exc)[:200]}"


# ── Circuit breaker ────────────────────────────────────────────


@dataclass
class _CircuitBreaker:
    name: str
    fail_threshold: int = 3
    window_s: float = 60.0
    open_duration_s: float = 30.0
    _failures: list[float] = field(default_factory=list)
    _opened_at: float | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def is_available(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return True
            if time.time() - self._opened_at >= self.open_duration_s:
                return True
            return False

    def record_success(self) -> None:
        with self._lock:
            self._failures.clear()
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            now = time.time()
            self._failures.append(now)
            self._failures = [t for t in self._failures if now - t <= self.window_s]
            if self._opened_at is None and len(self._failures) >= self.fail_threshold:
                self._opened_at = now
                log.warning("circuit[%s] → open", self.name)
            elif self._opened_at is not None and now - self._opened_at >= self.open_duration_s:
                self._opened_at = now


_BREAKERS: dict[str, _CircuitBreaker] = {}
_BREAKERS_LOCK = threading.Lock()


def _get_breaker(model: str) -> _CircuitBreaker:
    with _BREAKERS_LOCK:
        if model not in _BREAKERS:
            _BREAKERS[model] = _CircuitBreaker(name=model)
        return _BREAKERS[model]


# ── Core generate ──────────────────────────────────────────────


def _build_config(
    *,
    thinking_budget: int | None,
    model: str,
    system_instruction: str | None,
    response_mime_type: str | None,
    response_schema,
) -> types.GenerateContentConfig | None:
    kw: dict = {}
    if thinking_budget is not None and "pro" not in model and "lite" not in model:
        kw["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)
    if system_instruction:
        kw["system_instruction"] = system_instruction
    if response_mime_type:
        kw["response_mime_type"] = response_mime_type
    if response_schema is not None:
        kw["response_schema"] = response_schema
    return types.GenerateContentConfig(**kw) if kw else None


def _extract_usage(resp) -> tuple[int, int]:
    um = getattr(resp, "usage_metadata", None)
    if um is None:
        return 0, 0
    return (
        int(getattr(um, "prompt_token_count", 0) or 0),
        int(getattr(um, "candidates_token_count", 0) or 0),
    )


def _single_call(
    prompt,
    *,
    model: str,
    thinking_budget: int | None = 0,
    system_instruction: str | None = None,
    response_mime_type: str | None = None,
    response_schema=None,
) -> tuple[str, dict]:
    config = _build_config(
        thinking_budget=thinking_budget,
        model=model,
        system_instruction=system_instruction,
        response_mime_type=response_mime_type,
        response_schema=response_schema,
    )
    resp = get_client().models.generate_content(
        model=model, contents=prompt, config=config,
    )
    pt, ct = _extract_usage(resp)
    return (
        resp.text or "",
        {"model": model, "prompt_tokens": pt, "completion_tokens": ct, "cost_usd": cost_for(model, pt, ct)},
    )


def _retry_decorator(fn):
    return retry(
        stop=(stop_after_attempt(MAX_RETRY) | stop_after_delay(MAX_TOTAL_SECONDS)),
        wait=wait_exponential_jitter(initial=2, max=45),
        retry=retry_if_exception(is_overloaded),
        before_sleep=before_sleep_log(log, logging.WARNING),
        reraise=True,
    )(fn)


def _fallback_model() -> str:
    return os.getenv("LLM_FALLBACK_MODEL", "gemini-2.5-pro").strip() or "gemini-2.5-pro"


def _fallback_sequence(primary: str) -> list[str]:
    if os.getenv("AI_FORCE_MODEL", "").strip():
        return [primary]
    fb = _fallback_model()
    if not fb or fb == primary:
        return [primary]
    if not _get_breaker(primary).is_available():
        return [fb]
    return [primary, fb]


# ── Public API ─────────────────────────────────────────────────


def generate(
    prompt,
    *,
    model: str | None = None,
    thinking_budget: int | None = 0,
    system_instruction: str | None = None,
    response_mime_type: str | None = None,
    response_schema=None,
) -> tuple[str, dict]:
    """Gemini 텍스트 생성. 503 재시도 + fallback. 반환: (text, usage_dict)."""
    primary = resolve_model(model)
    kw = dict(
        thinking_budget=thinking_budget,
        system_instruction=system_instruction,
        response_mime_type=response_mime_type,
        response_schema=response_schema,
    )
    models = _fallback_sequence(primary)
    last_exc: Exception | None = None

    for i, m in enumerate(models):
        @_retry_decorator
        def _call():
            return _single_call(prompt, model=m, **kw)

        try:
            result = _call()
            if m == primary:
                _get_breaker(primary).record_success()
            return result
        except Exception as e:
            if not is_overloaded(e):
                raise
            last_exc = e
            log.warning("model=%s failed → next", m)
            if m == primary:
                _get_breaker(primary).record_failure()

    raise last_exc or RuntimeError("no models to try")


async def agenerate(
    prompt,
    *,
    model: str | None = None,
    thinking_budget: int | None = 0,
    system_instruction: str | None = None,
    response_mime_type: str | None = None,
    response_schema=None,
) -> tuple[str, dict]:
    """Async wrapper — runs sync generate in a thread."""
    import functools
    fn = functools.partial(
        generate,
        prompt,
        model=model,
        thinking_budget=thinking_budget,
        system_instruction=system_instruction,
        response_mime_type=response_mime_type,
        response_schema=response_schema,
    )
    return await asyncio.get_event_loop().run_in_executor(None, fn)
