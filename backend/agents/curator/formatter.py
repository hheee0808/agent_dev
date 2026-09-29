"""다이제스트 포맷터 — Slack mrkdwn 형식."""

from __future__ import annotations

from datetime import date

from backend.agents.curator.sources import Article

SOURCE_EMOJI = {
    "hn": ":newspaper:",
    "reddit": ":speech_balloon:",
    "github": ":octocat:",
    "arxiv": ":page_facing_up:",
}


def format_digest(articles: list[Article], today: date | None = None) -> str:
    today = today or date.today()
    lines = [f":robot_face: *AI Agent Dev Digest — {today.isoformat()}*\n"]

    for i, a in enumerate(articles, 1):
        emoji = SOURCE_EMOJI.get(a.source, ":link:")
        line = f"{i}. {emoji} <{a.url}|{a.title}>"
        if a.summary:
            line += f"\n    _{a.summary}_"
        lines.append(line)

    lines.append(f"\n_총 {len(articles)}건 · 자동 큐레이션 by agent-dev_")
    return "\n".join(lines)
