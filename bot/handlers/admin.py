"""Админ-панель — управление каналами, статистика и рассылка.
Команды:
  /admin — главное меню админки
"""
import asyncio
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.config import settings
from bot.database import async_session
from bot.database.crud import (
    add_channel,
    get_active_channels,
    get_all_user_ids,
    get_user_language,
    get_user_stats,
    remove_channel,
)
from bot.emojis import E, E_ID
from bot.i18n import t
from bot.keyboards.admin import (
    get_admin_keyboard,
    get_cancel_keyboard,
    get_channels_keyboard,
)

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_id_list


async def _get_lang(user_id: int) -> str:
    async with async_session() as session:
        return await get_user_language(session, user_id)


# ═══════════════ FSM ═══════════════

class AddChannelStates(StatesGroup):
    waiting_channel_id = State()
    waiting_title = State()
    waiting_invite_link = State()


class BroadcastStates(StatesGroup):
    waiting_message = State()
    confirming = State()


# ═══════════════ /admin ═══════════════

@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not is_admin(message.from_user.id):
        lang = await _get_lang(message.from_user.id)
        await message.answer(t("admin.no_access", lang))
        return

    lang = await _get_lang(message.from_user.id)
    await message.answer(
        t("admin.title", lang),
        reply_markup=get_admin_keyboard(lang),
        parse_mode="HTML",
    )


# ═══════════════ Статистика ═══════════════

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(f"{E['lock']} Нет доступа")
        return

    lang = await _get_lang(callback.from_user.id)

    async with async_session() as session:
        stats = await get_user_stats(session)

    try:
        await callback.message.edit_text(
            t("admin.stats", lang, **stats),
            reply_markup=get_admin_keyboard(lang),
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


# ═══════════════ Каналы ═══════════════

@router.callback_query(F.data == "admin_channels")
async def admin_channels(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(f"{E['lock']} Нет доступа")
        return

    lang = await _get_lang(callback.from_user.id)

    async with async_session() as session:
        channels = await get_active_channels(session)

    if not channels:
        text = t("admin.channels_empty", lang)
    else:
        lines = [t("admin.channels_title", lang)]
        for i, ch in enumerate(channels, 1):
            lines.append(
                f"{i}. <b>{ch.title}</b>\n"
                f"   ID: <code>{ch.channel_id}</code>\n"
                f"   {E['link']} {ch.invite_link}"
            )
        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=get_channels_keyboard(channels if channels else None, lang),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_channel")
async def start_add_channel(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(f"{E['lock']} Нет доступа")
        return

    lang = await _get_lang(callback.from_user.id)
    await state.update_data(lang=lang)

    await callback.message.edit_text(
        t("admin.add_channel_prompt", lang),
        reply_markup=get_cancel_keyboard(lang),
        parse_mode="HTML",
    )
    await state.set_state(AddChannelStates.waiting_channel_id)
    await callback.answer()


@router.message(AddChannelStates.waiting_channel_id)
async def process_channel_id(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    lang = data.get("lang", "ru")

    try:
        channel_id = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer(
            t("admin.id_not_number", lang),
            reply_markup=get_cancel_keyboard(lang),
        )
        return

    await state.update_data(channel_id=channel_id)
    await message.answer(
        t("admin.add_channel_title", lang),
        reply_markup=get_cancel_keyboard(lang),
    )
    await state.set_state(AddChannelStates.waiting_title)


@router.message(AddChannelStates.waiting_title)
async def process_title(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    lang = data.get("lang", "ru")

    title = (message.text or "").strip()
    if not title or len(title) > 200:
        await message.answer(
            t("error.generic", lang, msg="invalid title"),
            reply_markup=get_cancel_keyboard(lang),
        )
        return

    await state.update_data(title=title)
    await message.answer(
        t("admin.add_channel_link", lang),
        reply_markup=get_cancel_keyboard(lang),
        parse_mode="HTML",
    )
    await state.set_state(AddChannelStates.waiting_invite_link)


@router.message(AddChannelStates.waiting_invite_link)
async def process_invite_link(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    lang = data.get("lang", "ru")

    raw = (message.text or "").strip()
    invite_link = _normalize_channel_link(raw)
    if not invite_link:
        await message.answer(
            t("admin.link_invalid", lang),
            reply_markup=get_cancel_keyboard(lang),
        )
        return

    await state.clear()

    try:
        async with async_session() as session:
            channel = await add_channel(
                session=session,
                channel_id=data["channel_id"],
                title=data["title"],
                invite_link=invite_link,
            )
        await message.answer(
            t("admin.add_channel_success", lang, title=channel.title),
            reply_markup=get_admin_keyboard(lang),
            parse_mode="HTML",
        )
    except ValueError as e:
        await message.answer(
            t("admin.add_channel_error", lang, msg=str(e)),
            reply_markup=get_admin_keyboard(lang),
            parse_mode="HTML",
        )


# ═══════════════ Удаление канала ═══════════════

@router.callback_query(F.data.startswith("admin_del_"))
async def confirm_delete_channel(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(f"{E['lock']} Нет доступа")
        return

    lang = await _get_lang(callback.from_user.id)
    channel_id = callback.data.replace("admin_del_", "")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=t("btn.admin_confirm_del", lang),
                callback_data=f"admin_confirm_del_{channel_id}",
                style="danger",
                icon_custom_emoji_id=E_ID["trash"],
            ),
            InlineKeyboardButton(
                text=t("btn.admin_cancel_del", lang),
                callback_data="admin_channels",
                style="success",
                icon_custom_emoji_id=E_ID["check"],
            ),
        ],
    ])

    await callback.message.edit_text(
        t("admin.confirm_delete", lang, channel_id=channel_id),
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_confirm_del_"))
async def delete_channel(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(f"{E['lock']} Нет доступа")
        return

    channel_id = int(callback.data.replace("admin_confirm_del_", ""))

    async with async_session() as session:
        removed = await remove_channel(session, channel_id)

    if removed:
        lang = await _get_lang(callback.from_user.id)
        await callback.answer(t("admin.channel_removed", lang))
    else:
        await callback.answer(f"{E['cross']} not found")

    await admin_channels(callback)


# ═══════════════ Отмена FSM ═══════════════

@router.callback_query(F.data == "admin_cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    lang = await _get_lang(callback.from_user.id)
    await callback.message.edit_text(
        t("admin.title", lang),
        reply_markup=get_admin_keyboard(lang),
        parse_mode="HTML",
    )
    await callback.answer()


def _normalize_channel_link(raw: str) -> str | None:
    """Приводит ввод к формату https://t.me/..."""
    raw = raw.strip()

    if raw.startswith("https://t.me/"):
        return raw
    if raw.startswith("https://telegram.me/"):
        return raw.replace("https://telegram.me/", "https://t.me/")
    if raw.startswith("http://t.me/"):
        return raw.replace("http://", "https://")

    if raw.startswith("@"):
        username = raw[1:]
        if username and username.isascii():
            return f"https://t.me/{username}"
        return None

    if raw.isascii() and " " not in raw and len(raw) > 2:
        return f"https://t.me/{raw}"

    return None


# ═══════════════ Рассылка ═══════════════

@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(f"{E['lock']} Нет доступа")
        return

    lang = await _get_lang(callback.from_user.id)
    await state.update_data(lang=lang)

    await callback.message.edit_text(
        t("admin.broadcast_prompt", lang),
        reply_markup=get_cancel_keyboard(lang),
        parse_mode="HTML",
    )
    await state.set_state(BroadcastStates.waiting_message)
    await callback.answer()


@router.message(BroadcastStates.waiting_message)
async def preview_broadcast(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    lang = data.get("lang", "ru")

    msg_data: dict = {"type": "text", "text": message.text or message.caption or ""}
    if message.photo:
        msg_data["type"] = "photo"
        msg_data["file_id"] = message.photo[-1].file_id
    elif message.video:
        msg_data["type"] = "video"
        msg_data["file_id"] = message.video.file_id

    await state.update_data(broadcast_msg=msg_data)

    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=t("btn.admin_broadcast_confirm", lang),
                callback_data="admin_broadcast_confirm",
                style="success",
                icon_custom_emoji_id=E_ID["check"],
            ),
            InlineKeyboardButton(
                text=t("btn.admin_cancel", lang),
                callback_data="admin_cancel",
                style="danger",
                icon_custom_emoji_id=E_ID["cross"],
            ),
        ],
    ])

    if msg_data["type"] == "photo":
        await message.answer_photo(
            msg_data["file_id"],
            caption=msg_data["text"] or None,
        )
    elif msg_data["type"] == "video":
        await message.answer_video(
            msg_data["file_id"],
            caption=msg_data["text"] or None,
        )
    else:
        await message.answer(msg_data["text"])

    await message.answer(
        t("admin.broadcast_preview", lang),
        reply_markup=confirm_kb,
    )
    await state.set_state(BroadcastStates.confirming)


@router.callback_query(F.data == "admin_broadcast_confirm")
async def confirm_broadcast(
    callback: CallbackQuery, state: FSMContext,
) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(f"{E['lock']} Нет доступа")
        return

    data = await state.get_data()
    lang = data.get("lang", "ru")
    msg_data = data.get("broadcast_msg")
    await state.clear()

    if not msg_data:
        await callback.answer(f"{E['cross']} no message")
        return

    await callback.message.edit_text(
        t("admin.broadcast_started", lang),
        parse_mode="HTML",
    )
    await callback.answer()

    async with async_session() as session:
        user_ids = await get_all_user_ids(session)

    bot_info = await callback.bot.get_me()
    skip_ids = {bot_info.id} | set(settings.admin_id_list)
    user_ids = [uid for uid in user_ids if uid not in skip_ids]

    bot = callback.bot
    success = 0
    failed = 0

    for user_id in user_ids:
        try:
            if msg_data["type"] == "photo":
                await bot.send_photo(
                    user_id,
                    msg_data["file_id"],
                    caption=msg_data["text"] or None,
                )
            elif msg_data["type"] == "video":
                await bot.send_video(
                    user_id,
                    msg_data["file_id"],
                    caption=msg_data["text"] or None,
                )
            else:
                await bot.send_message(user_id, msg_data["text"])
            success += 1
        except Exception as e:
            logger.warning(f"Рассылка: не доставлено {user_id}: {e}")
            failed += 1

        if (success + failed) % 25 == 0:
            await asyncio.sleep(1)

    await callback.message.answer(
        t("admin.broadcast_done", lang, success=success, failed=failed),
        reply_markup=get_admin_keyboard(lang),
        parse_mode="HTML",
    )
