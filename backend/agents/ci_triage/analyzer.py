"""CI 로그 분석 — Gemini로 원인·재현·해결안 추출."""

from __future__ import annotations

import json
import logging

from backend.common.llm import generate

log = logging.getLogger(__name__)

ANALYZE_SYSTEM_PROMPT = """\
You are a CI/CD failure analyst. Given a GitHub Actions workflow log,
analyze the failure and provide:

1. **Root Cause**: What exactly failed and why
2. **Reproduction**: Steps to reproduce locally
3. **Fix Suggestion**: Concrete steps to fix the issue
4. **Severity**: low / medium / high / critical

Return JSON:
{
  "root_cause": "...",
  "reproduction": "...",
  "fix_suggestion": "...",
  "severity": "medium",
  "failed_step": "...",
  "error_type": "build | test | lint | deploy | dependency | config"
}
"""


def analyze_log(log_text: str, run_url: str = "") -> dict:
    """CI 로그 분석 → 구조화된 결과."""
    truncated = log_text[-8000:]

    prompt = f"Analyze this CI failure log:\n\nRun URL: {run_url}\n\n```\n{truncated}\n```"

    text, usage = generate(
        prompt,
        system_instruction=ANALYZE_SYSTEM_PROMPT,
        response_mime_type="application/json",
    )

    try:
        result = json.loads(text)
        result["usage"] = usage
        return result
    except json.JSONDecodeError:
        log.warning("analyze JSON parse failed")
        return {
            "root_cause": text[:500],
            "reproduction": "",
            "fix_suggestion": "",
            "severity": "unknown",
            "error_type": "unknown",
            "usage": usage,
        }


def format_pr_comment(analysis: dict, run_url: str = "") -> str:
    """분석 결과를 PR 코멘트 마크다운으로 포맷."""
    severity_emoji = {
        "low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴",
    }
    sev = analysis.get("severity", "unknown")
    emoji = severity_emoji.get(sev, "⚪")

    parts = [
        f"## {emoji} CI Failure Analysis",
        "",
        f"**Severity**: {sev} | **Type**: {analysis.get('error_type', 'unknown')}",
    ]

    if run_url:
        parts.append(f"**Run**: {run_url}")

    parts.extend([
        "",
        f"### Root Cause\n{analysis.get('root_cause', 'N/A')}",
        "",
        f"### Reproduction\n{analysis.get('reproduction', 'N/A')}",
        "",
        f"### Fix Suggestion\n{analysis.get('fix_suggestion', 'N/A')}",
        "",
        "_Automated analysis by agent-dev CI triage_",
    ])

    return "\n".join(parts)
