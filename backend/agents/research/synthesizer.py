"""리서치 합성 — sub-question 결과를 인용 포함 리포트로 종합."""

from __future__ import annotations

import logging

from backend.common.llm import generate

log = logging.getLogger(__name__)

SYNTH_SYSTEM_PROMPT = """\
You are a research report writer. Given a main question and research findings from multiple sub-questions,
write a comprehensive report.

Rules:
- Use markdown formatting with ## headers for each section
- Cite sources inline using [n] numbered references
- Include a ## References section at the end with all URLs
- Answer in the same language as the original question
- Be thorough but concise — aim for 500-1000 words
- If findings conflict, note the disagreement
- End with a brief ## Conclusion
"""

CRITIQUE_SYSTEM_PROMPT = """\
You are a research quality critic. Review the report and identify:
1. Claims without citations
2. Missing perspectives or angles
3. Logical gaps or unsupported conclusions

If the report is good, respond with "PASS".
Otherwise, list specific issues to fix (max 3).
Keep response under 200 words.
"""


def synthesize(question: str, findings: list[dict]) -> tuple[str, dict]:
    """findings를 종합해 리포트 생성. 반환: (report_md, usage)."""
    context_parts = []
    all_sources = []
    for f in findings:
        context_parts.append(f"### Sub-question: {f['query']}\n{f['content']}")
        all_sources.extend(f.get("sources", []))

    context = "\n\n".join(context_parts)
    sources_list = "\n".join(f"[{i+1}] {s}" for i, s in enumerate(dict.fromkeys(all_sources)))

    prompt = (
        f"Main question: {question}\n\n"
        f"Research findings:\n{context}\n\n"
        f"Available sources:\n{sources_list}"
    )

    report, usage = generate(prompt, system_instruction=SYNTH_SYSTEM_PROMPT)
    return report, usage


def critique(report: str) -> str:
    """self-critique — 리포트 품질 검증."""
    text, _ = generate(
        f"Review this research report:\n\n{report}",
        system_instruction=CRITIQUE_SYSTEM_PROMPT,
    )
    return text.strip()
