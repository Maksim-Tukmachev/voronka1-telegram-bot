"""Funnel handlers: /start → subscribe check → video → schedule follow-up."""

from __future__ import annotations

import logging
import time

from aiogram import F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot import texts
from bot.config import Settings
from bot.followup import FollowUpScheduler, FollowUpStore

logger = logging.getLogger(__name__)

CALLBACK_SUBSCRIBED = "check_subscribed"

def _is_subscribed(member) -> bool:
    status = member.status
    if status in {
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.CREATOR,
    }:
        return True
    if status == ChatMemberStatus.RESTRICTED:
        return bool(getattr(member, "is_member", False))
    return False


def build_router(
    settings: Settings,
    store: FollowUpStore,
    scheduler: FollowUpScheduler,
) -> Router:
    router = Router(name="funnel")

    def subscribe_keyboard() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=texts.BTN_SUBSCRIBE,
                        url=settings.channel_url,
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=texts.BTN_I_SUBSCRIBED,
                        callback_data=CALLBACK_SUBSCRIBED,
                    )
                ],
            ]
        )

    def video_keyboard() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=texts.BTN_AUDIT,
                        url=settings.audit_url,
                    )
                ],
            ]
        )

    @router.message(CommandStart())
    async def on_start(message: Message) -> None:
        await message.answer(texts.GREETING)
        await message.answer(texts.SUBSCRIBE_PROMPT, reply_markup=subscribe_keyboard())

    @router.callback_query(F.data == CALLBACK_SUBSCRIBED)
    async def on_subscribed(callback: CallbackQuery) -> None:
        await callback.answer()
        if callback.from_user is None or callback.message is None:
            return

        user_id = callback.from_user.id
        try:
            member = await callback.bot.get_chat_member(settings.channel_ref, user_id)
        except Exception:
            logger.exception(
                "getChatMember failed for user_id=%s channel=%s",
                user_id,
                settings.channel_ref,
            )
            await callback.message.answer(texts.MEMBERSHIP_CHECK_FAILED)
            return

        if not _is_subscribed(member):
            await callback.message.answer(
                texts.NOT_SUBSCRIBED,
                reply_markup=subscribe_keyboard(),
            )
            return

        await callback.message.answer(
            texts.VIDEO_DELIVERED.format(
                video_url=settings.video_url,
                audit_url=settings.audit_url,
            ),
            reply_markup=video_keyboard(),
            disable_web_page_preview=False,
        )

        due_at = time.time() + settings.followup_delay_seconds
        store.schedule(callback.message.chat.id, due_at)
        scheduler.notify_scheduled()
        logger.info(
            "Video delivered to chat_id=%s; follow-up due in %ss",
            callback.message.chat.id,
            settings.followup_delay_seconds,
        )

    return router
