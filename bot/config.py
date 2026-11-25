"""Load settings from environment / .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    channel_ref: str | int
    channel_url: str
    video_url: str
    audit_url: str
    followup_delay_seconds: int
    followup_db_path: Path


def _channel_ref() -> str | int:
    raw_id = os.getenv("CHANNEL_ID", "").strip()
    if raw_id:
        return int(raw_id)
    username = os.getenv("CHANNEL_USERNAME", "@samartsevvv").strip()
    if not username:
        raise ValueError("Set CHANNEL_USERNAME or CHANNEL_ID")
    return username


def load_settings() -> Settings:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token or token.startswith("0000000000"):
        raise ValueError(
            "TELEGRAM_BOT_TOKEN is missing. Copy .env.example to .env and set a real token."
        )

    delay_raw = os.getenv("FOLLOWUP_DELAY_SECONDS", "1200").strip()
    try:
        delay = int(delay_raw)
    except ValueError as exc:
        raise ValueError("FOLLOWUP_DELAY_SECONDS must be an integer") from exc
    if delay < 1:
        raise ValueError("FOLLOWUP_DELAY_SECONDS must be >= 1")

    db_path = Path(os.getenv("FOLLOWUP_DB_PATH", "data/followups.db"))

    return Settings(
        bot_token=token,
        channel_ref=_channel_ref(),
        channel_url=os.getenv("CHANNEL_URL", "https://t.me/samartsevvv").strip(),
        video_url=os.getenv("VIDEO_URL", "https://example.com/video-stub").strip(),
        audit_url=os.getenv("AUDIT_URL", "https://t.me/power_of_sales").strip(),
        followup_delay_seconds=delay,
        followup_db_path=db_path,
    )
