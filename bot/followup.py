"""SQLite-backed follow-up jobs + in-process asyncio scheduler."""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import time
from pathlib import Path

from aiogram import Bot

from bot import texts

logger = logging.getLogger(__name__)


class FollowUpStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS followups (
                    chat_id INTEGER PRIMARY KEY,
                    due_at REAL NOT NULL,
                    sent INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.commit()

    def schedule(self, chat_id: int, due_at: float) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO followups (chat_id, due_at, sent)
                VALUES (?, ?, 0)
                ON CONFLICT(chat_id) DO UPDATE SET
                    due_at = excluded.due_at,
                    sent = 0
                """,
                (chat_id, due_at),
            )
            conn.commit()

    def mark_sent(self, chat_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE followups SET sent = 1 WHERE chat_id = ?",
                (chat_id,),
            )
            conn.commit()

    def due_jobs(self, now: float | None = None) -> list[int]:
        now = time.time() if now is None else now
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT chat_id FROM followups
                WHERE sent = 0 AND due_at <= ?
                ORDER BY due_at ASC
                """,
                (now,),
            ).fetchall()
        return [int(row["chat_id"]) for row in rows]

    def pending_future(self, now: float | None = None) -> list[tuple[int, float]]:
        now = time.time() if now is None else now
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT chat_id, due_at FROM followups
                WHERE sent = 0 AND due_at > ?
                ORDER BY due_at ASC
                """,
                (now,),
            ).fetchall()
        return [(int(row["chat_id"]), float(row["due_at"])) for row in rows]


class FollowUpScheduler:
    """Wake periodically; send due reminders. Survives restart via SQLite."""

    def __init__(
        self,
        bot: Bot,
        store: FollowUpStore,
        audit_url: str,
        poll_interval: float = 5.0,
    ) -> None:
        self.bot = bot
        self.store = store
        self.audit_url = audit_url
        self.poll_interval = poll_interval
        self._task: asyncio.Task[None] | None = None
        self._wake = asyncio.Event()

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="followup-scheduler")

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()

    def notify_scheduled(self) -> None:
        self._wake.set()

    async def _run(self) -> None:
        logger.info("Follow-up scheduler started")
        try:
            while True:
                await self._flush_due()
                self._wake.clear()
                try:
                    await asyncio.wait_for(self._wake.wait(), timeout=self.poll_interval)
                except asyncio.TimeoutError:
                    pass
        except asyncio.CancelledError:
            logger.info("Follow-up scheduler stopped")
            raise

    async def _flush_due(self) -> None:
        for chat_id in self.store.due_jobs():
            try:
                await self.bot.send_message(
                    chat_id,
                    texts.FOLLOWUP.format(audit_url=self.audit_url),
                )
                self.store.mark_sent(chat_id)
                logger.info("Follow-up sent to chat_id=%s", chat_id)
            except Exception:
                logger.exception("Failed to send follow-up to chat_id=%s", chat_id)
