"""GitHub API 클라이언트 — Actions 로그 조회 + PR 코멘트."""

from __future__ import annotations

import logging
import os

import httpx

log = logging.getLogger(__name__)

BASE = "https://api.github.com"


def _headers() -> dict:
    token = os.getenv("GITHUB_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _repo() -> str:
    return os.getenv("GITHUB_REPO", "")


async def get_failed_runs(limit: int = 5) -> list[dict]:
    """최근 실패한 workflow runs."""
    async with httpx.AsyncClient(timeout=15, headers=_headers()) as c:
        r = await c.get(
            f"{BASE}/repos/{_repo()}/actions/runs",
            params={"status": "failure", "per_page": limit},
        )
        if r.status_code != 200:
            log.warning("GitHub runs API: %d", r.status_code)
            return []
        return r.json().get("workflow_runs", [])


async def get_run_logs(run_id: int) -> str:
    """workflow run의 로그 텍스트 (jobs → steps → 실패 step 로그)."""
    async with httpx.AsyncClient(timeout=15, headers=_headers()) as c:
        r = await c.get(f"{BASE}/repos/{_repo()}/actions/runs/{run_id}/jobs")
        if r.status_code != 200:
            return f"Failed to fetch jobs: {r.status_code}"

        jobs = r.json().get("jobs", [])
        log_parts = []
        for job in jobs:
            if job.get("conclusion") != "failure":
                continue
            job_name = job.get("name", "unknown")
            for step in job.get("steps", []):
                if step.get("conclusion") == "failure":
                    log_parts.append(
                        f"Job: {job_name}\n"
                        f"Step: {step.get('name', 'unknown')}\n"
                        f"Status: {step.get('conclusion')}"
                    )

        if not log_parts:
            return "No failed steps found in jobs."
        return "\n\n---\n\n".join(log_parts)


async def get_run_log_text(run_id: int) -> str:
    """workflow run의 raw 로그 다운로드 (zip → 텍스트 추출)."""
    async with httpx.AsyncClient(timeout=30, headers=_headers(), follow_redirects=True) as c:
        r = await c.get(f"{BASE}/repos/{_repo()}/actions/runs/{run_id}/logs")
        if r.status_code != 200:
            return await get_run_logs(run_id)

        import io, zipfile
        try:
            z = zipfile.ZipFile(io.BytesIO(r.content))
            texts = []
            for name in z.namelist():
                if name.endswith(".txt"):
                    content = z.read(name).decode("utf-8", errors="replace")
                    if "##[error]" in content or "FAILED" in content or "Error" in content:
                        texts.append(f"=== {name} ===\n{content[-3000:]}")
            return "\n\n".join(texts) if texts else await get_run_logs(run_id)
        except Exception as e:
            log.warning("log zip parse failed: %s", e)
            return await get_run_logs(run_id)


async def post_pr_comment(pr_number: int, body: str) -> bool:
    """PR에 코멘트 작성."""
    async with httpx.AsyncClient(timeout=15, headers=_headers()) as c:
        r = await c.post(
            f"{BASE}/repos/{_repo()}/issues/{pr_number}/comments",
            json={"body": body},
        )
        if r.status_code == 201:
            log.info("PR #%d comment posted", pr_number)
            return True
        log.warning("PR comment failed: %d %s", r.status_code, r.text[:200])
        return False


async def find_pr_for_sha(sha: str) -> int | None:
    """커밋 SHA로 관련 PR 번호 찾기."""
    async with httpx.AsyncClient(timeout=15, headers=_headers()) as c:
        r = await c.get(f"{BASE}/repos/{_repo()}/commits/{sha}/pulls")
        if r.status_code == 200:
            prs = r.json()
            if prs:
                return prs[0].get("number")
    return None
