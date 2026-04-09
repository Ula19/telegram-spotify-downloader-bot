"""Rate limiting — ограничение частоты запросов на скачивание
Лимит: 5 запросов в минуту на юзера
Хранение в памяти — без Redis/БД, сбрасывается при перезапуске
"""
import time
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from bot.i18n import detect_language, t

logger = logging.getLogger(__name__)

MAX_REQUESTS = 5
WINDOW_SECONDS = 60

# {user_id: [timestamp1, timestamp2, ...]}
_user_requests: dict[int, list[float]] = {}


def cleanup_stale_entries() -> int:
    """Удаляет протухшие записи из _user_requests."""
    now = time.time()
    stale_users = [
        uid for uid, timestamps in _user_requests.items()
        if not any(now - ts < WINDOW_SECONDS for ts in timestamps)
    ]
    for uid in stale_users:
        del _user_requests[uid]
    if stale_users:
        logger.debug("Rate limit: удалено %d устаревших записей", len(stale_users))
    return len(stale_users)


class RateLimitMiddleware(BaseMiddleware):
    """Ограничивает частоту скачиваний — только для текстовых сообщений со ссылками Spotify"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.text:
            return await handler(event, data)

        from bot.utils.helpers import is_spotify_url
        if not is_spotify_url(event.text.strip()):
            return await handler(event, data)

        user_id = event.from_user.id
        now = time.time()

        if user_id in _user_requests:
            _user_requests[user_id] = [
                ts for ts in _user_requests[user_id]
                if now - ts < WINDOW_SECONDS
            ]
        else:
            _user_requests[user_id] = []

        if len(_user_requests[user_id]) >= MAX_REQUESTS:
            oldest = _user_requests[user_id][0]
            wait_sec = int(WINDOW_SECONDS - (now - oldest)) + 1
            lang = detect_language(event.from_user.language_code)
            await event.answer(
                t("error.rate_limit", lang, seconds=wait_sec),
            )
            logger.info(f"Rate limit для {user_id}: подождать {wait_sec} сек")
            return None

        _user_requests[user_id].append(now)
        return await handler(event, data)
