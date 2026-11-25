"""Entry point: python -m bot"""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher

from bot.config import load_settings
from bot.followup import FollowUpScheduler, FollowUpStore
from bot.handlers import build_router


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        settings = load_settings()
    except ValueError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(_run(settings))


async def _run(settings) -> None:
    bot = Bot(token=settings.bot_token)
    store = FollowUpStore(settings.followup_db_path)
    scheduler = FollowUpScheduler(
        bot=bot,
        store=store,
        audit_url=settings.audit_url,
    )
    dp = Dispatcher()
    dp.include_router(build_router(settings, store, scheduler))

    pending = store.pending_future()
    if pending:
        logging.getLogger(__name__).info(
            "Restored %s pending follow-up(s) from %s",
            len(pending),
            settings.followup_db_path,
        )

    scheduler.start()
    logging.getLogger(__name__).info("Bot starting (polling)")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.stop()
        await bot.session.close()


if __name__ == "__main__":
    main()
