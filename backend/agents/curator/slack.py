"""Slack 발송."""

from __future__ import annotations

import logging
import os

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

log = logging.getLogger(__name__)


def send_digest(text: str, channel: str | None = None) -> bool:
    token = os.getenv("SLACK_BOT_TOKEN", "").strip()
    if not token:
        log.warning("SLACK_BOT_TOKEN 미설정 → 발송 skip")
        return False

    channel = channel or os.getenv("SLACK_DIGEST_CHANNEL", "#dev-digest")
    client = WebClient(token=token)

    try:
        client.chat_postMessage(channel=channel, text=text, mrkdwn=True)
        log.info("Slack 발송 완료: channel=%s len=%d", channel, len(text))
        return True
    except SlackApiError as e:
        log.error("Slack 발송 실패: %s", e.response["error"])
        return False
