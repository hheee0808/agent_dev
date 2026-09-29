"""소스별 데이터 수집 — HN, Reddit, GitHub Trending, arXiv."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

log = logging.getLogger(__name__)

TIMEOUT = 15


@dataclass
class Article:
    title: str
    url: str
    source: str
    score: int = 0
    summary: str = ""


async def fetch_hn(limit: int = 30) -> list[Article]:
    """Hacker News top stories."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get("https://hacker-news.firebaseio.com/v0/topstories.json")
        ids = r.json()[:limit]
        articles = []
        for sid in ids:
            item = (await c.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")).json()
            if not item or item.get("type") != "story":
                continue
            articles.append(Article(
                title=item.get("title", ""),
                url=item.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                source="hn",
                score=item.get("score", 0),
            ))
        log.info("HN: %d articles fetched", len(articles))
        return articles


async def fetch_reddit(subreddit: str = "MachineLearning", limit: int = 25) -> list[Article]:
    """Reddit hot posts."""
    headers = {"User-Agent": "agent-dev/0.1"}
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers) as c:
        r = await c.get(f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}")
        data = r.json().get("data", {}).get("children", [])
        articles = []
        for item in data:
            d = item.get("data", {})
            if d.get("stickied"):
                continue
            articles.append(Article(
                title=d.get("title", ""),
                url=d.get("url", ""),
                source="reddit",
                score=d.get("score", 0),
            ))
        log.info("Reddit r/%s: %d articles fetched", subreddit, len(articles))
        return articles


async def fetch_github_trending(language: str = "python", since: str = "daily") -> list[Article]:
    """GitHub trending via unofficial API."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(
            f"https://api.gitterapp.com/repositories?language={language}&since={since}",
        )
        if r.status_code != 200:
            log.warning("GitHub trending API returned %d, trying scrape fallback", r.status_code)
            return await _github_trending_scrape(language)
        repos = r.json()
        articles = []
        for repo in repos[:25]:
            articles.append(Article(
                title=f"{repo.get('author', '')}/{repo.get('name', '')} — {repo.get('description', '')}",
                url=repo.get("url", ""),
                source="github",
                score=repo.get("stars", 0),
            ))
        log.info("GitHub trending: %d repos fetched", len(articles))
        return articles


async def _github_trending_scrape(language: str) -> list[Article]:
    """GitHub trending 페이지 직접 파싱 (API 실패 시 fallback)."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        r = await c.get(f"https://github.com/trending/{language}?since=daily")
        if r.status_code != 200:
            log.warning("GitHub trending scrape also failed: %d", r.status_code)
            return []
        articles = []
        for line in r.text.split('href="/'):
            if "/stargazers" in line or len(articles) >= 20:
                continue
            parts = line.split('"')[0].split("/")
            if len(parts) == 2 and parts[0] and parts[1]:
                repo = f"{parts[0]}/{parts[1]}"
                if not any(a.title.startswith(repo) for a in articles):
                    articles.append(Article(
                        title=repo,
                        url=f"https://github.com/{repo}",
                        source="github",
                    ))
        log.info("GitHub trending (scrape): %d repos", len(articles))
        return articles


async def fetch_arxiv(query: str = "cat:cs.AI OR cat:cs.CL OR cat:cs.LG", max_results: int = 20) -> list[Article]:
    """arXiv recent papers."""
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as c:
        r = await c.get(
            "https://export.arxiv.org/api/query",
            params={"search_query": query, "sortBy": "submittedDate", "sortOrder": "descending", "max_results": max_results},
        )
        articles = []
        for entry in r.text.split("<entry>")[1:]:
            title = _extract_xml(entry, "title").replace("\n", " ").strip()
            link = _extract_xml(entry, "id").strip()
            for part in entry.split("<link"):
                if 'title="pdf"' in part and 'href="' in part:
                    link = part.split('href="')[1].split('"')[0]
                    break
            summary = _extract_xml(entry, "summary").replace("\n", " ").strip()[:300]
            if title and title != link:
                articles.append(Article(title=title, url=link, source="arxiv", summary=summary))
        log.info("arXiv: %d papers fetched", len(articles))
        return articles


def _extract_xml(text: str, tag: str) -> str:
    start = text.find(f"<{tag}>")
    end = text.find(f"</{tag}>")
    if start == -1 or end == -1:
        return ""
    return text[start + len(tag) + 2:end]


async def fetch_all() -> list[Article]:
    """모든 소스에서 병렬 수집."""
    import asyncio
    results = await asyncio.gather(
        fetch_hn(),
        fetch_reddit("MachineLearning"),
        fetch_reddit("LocalLLaMA"),
        fetch_github_trending("python"),
        fetch_arxiv(),
        return_exceptions=True,
    )
    articles = []
    for r in results:
        if isinstance(r, Exception):
            log.warning("source fetch failed: %s", r)
            continue
        articles.extend(r)
    log.info("total articles collected: %d", len(articles))
    return articles
