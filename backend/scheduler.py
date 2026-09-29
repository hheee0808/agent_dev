"""APScheduler — 매일 07:00 큐레이션 다이제스트 발송."""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

log = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _run_curator():
    from backend.agents.curator.agent import CuratorAgent
    agent = CuratorAgent()
    result = asyncio.run(agent.safe_run({"trigger": "cron"}))
    if result.error:
        log.error("curator cron failed: %s", result.error)
    else:
        log.info("curator cron done: %s", result.usage)


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_curator,
        trigger="cron",
        hour=7,
        minute=0,
        id="daily_curator",
        replace_existing=True,
    )
    _scheduler.start()
    log.info("scheduler started — curator runs daily at 07:00")
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("scheduler stopped")
