"""Доменный хэндлер — скачивание одного трека со Spotify.

Флоу:
1. Юзер присылает ссылку на трек Spotify (/track/<id>).
2. handle_spotify_link → process_spotify_url.
3. downloader.get_track → метаданные + прямая mp3-ссылка (RapidAPI).
4. Проверяем кэш (file_id в БД) → если есть, отдаём мгновенно.
5. Иначе downloader.download_track → скачиваем mp3 в /tmp/spotify_bot/,
   отправляем аудио в Telegram, сохраняем file_id в кэш, удаляем файл.

Альбомы и плейлисты на MVP не поддерживаются — отвечаем `only_tracks_supported`.
Подкасты/эпизоды — `not_supported`.
"""
import asyncio
import logging
import time

from aiogram import Bot, F, Router
from aiogram.types import FSInputFile, Message, User as TgUser

from bot.config import settings
from bot.database import async_session
from bot.database.crud import (
    get_cached_download,
    get_user_language,
    increment_download_count,
    save_download,
)
from bot.emojis import E
from bot.i18n import t
from bot.keyboards.inline import get_back_keyboard
from bot.services.spotify import (
    DownloadResult,
    SpotifyAPIDown,
    SpotifyError,
    SpotifyNotSupported,
    SpotifyTrackUnavailable,
    TrackInfo,
    downloader,
)
from bot.utils.helpers import (
    clean_spotify_url,
    format_duration,
    is_spotify_album_or_playlist,
    is_spotify_unsupported_url,
    is_spotify_url,
)

logger = logging.getLogger(__name__)
router = Router()

FORMAT_KEY = "mp3_rapidapi"


# ═══════════════════ Fallback alerts ═══════════════════

_alert_last_sent: dict[str, float] = {}
_ALERT_COOLDOWN = 600  # 10 минут на один ключ


def _classify_error(msg: str) -> str:
    m = msg.lower()
    if "401" in m or "403" in m:
        return "auth"
    if "429" in m or "quota" in m or "limit" in m:
        return "quota"
    if "5" in m[:3] or "server" in m or "timeout" in m:
        return "network"
    return "unknown"


def setup_fallback_alerts(bot: Bot) -> None:
    """Подключает callback отправки алертов админам к downloader.on_source_failed."""
    loop = asyncio.get_event_loop()

    def _on_failed(source: str, msg: str) -> None:
        category = _classify_error(msg)
        key = f"{source}:{category}"
        now = time.time()
        if now - _alert_last_sent.get(key, 0) < _ALERT_COOLDOWN:
            return
        _alert_last_sent[key] = now
        asyncio.run_coroutine_threadsafe(_send_alert(bot, source, msg), loop)

    downloader.on_source_failed = _on_failed


async def _send_alert(bot: Bot, source: str, msg: str) -> None:
    for admin_id in settings.admin_id_list:
        try:
            async with async_session() as session:
                lang = await get_user_language(session, admin_id)
            await bot.send_message(
                admin_id,
                t("admin.alert_source_failed", lang,
                  source=source, msg=msg[:500]),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning("Не удалось отправить алерт %s: %s", admin_id, e)


# ═══════════════════ Обработка входящего сообщения ═══════════════════

@router.message(F.text)
async def handle_spotify_link(message: Message) -> None:
    """Ловит все текстовые сообщения, реагирует только на ссылки Spotify."""
    text = (message.text or "").strip()

    # Подкаст/эпизод — явно не поддерживается
    if is_spotify_unsupported_url(text):
        lang = await _get_lang(message.from_user.id)
        await message.answer(
            t("download.not_supported", lang),
            parse_mode="HTML",
        )
        return

    # Альбом/плейлист — на MVP только треки
    if is_spotify_album_or_playlist(text):
        lang = await _get_lang(message.from_user.id)
        await message.answer(
            t("download.only_tracks_supported", lang),
            parse_mode="HTML",
        )
        return

    # Не наш домен — молчим, чтобы не спамить на любой текст
    if not is_spotify_url(text):
        return

    lang = await _get_lang(message.from_user.id)
    await process_spotify_url(message, text, message.from_user, lang)


async def process_spotify_url(
    message: Message,
    url: str,
    user: TgUser,
    lang: str,
) -> None:
    """Главная функция обработки ссылки на трек Spotify.
    Вызывается также из check_subscription при pending_url.
    """
    canonical_url = clean_spotify_url(url)

    # ───── Кэш проверяем ДО провайдеров ─────
    # так закэшированный трек уедет юзеру мгновенно и даже когда все движки лежат
    async with async_session() as session:
        cached = await get_cached_download(session, canonical_url, FORMAT_KEY)

    if cached:
        try:
            await message.answer_audio(
                cached.file_id,
                title=cached.title or None,
            )
            async with async_session() as session:
                await increment_download_count(session, user.id)
            return
        except Exception as e:
            logger.warning("Кэш битый, качаем заново: %s", e)

    progress = await message.answer(
        t("download.fetching_info", lang),
        parse_mode="HTML",
    )

    # показываем метадату, как только её отдал первый рабочий провайдер
    async def _on_metadata(track: TrackInfo) -> None:
        try:
            await progress.edit_text(
                t("download.track_info", lang,
                  title=track.title,
                  artist=track.artist_line or "—",
                  album=track.album or "—",
                  duration=format_duration(track.duration)),
                parse_mode="HTML",
            )
        except Exception:
            pass

    result: DownloadResult | None = None
    try:
        # ───── Добыча трека через цепочку провайдеров ─────
        try:
            track, result = await downloader.fetch(canonical_url, on_metadata=_on_metadata)
        except SpotifyNotSupported:
            await progress.edit_text(
                t("download.only_tracks_supported", lang),
                parse_mode="HTML",
            )
            return
        except SpotifyTrackUnavailable:  # трека нет ни в одном источнике (не сбой)
            await progress.edit_text(
                t("error.track_unavailable", lang),
                parse_mode="HTML",
                reply_markup=get_back_keyboard(lang),
            )
            return
        except SpotifyAPIDown:  # сюда же попадает SpotifyAllProvidersFailed
            await progress.edit_text(
                t("error.spotify_api_down", lang),
                parse_mode="HTML",
                reply_markup=get_back_keyboard(lang),
            )
            return
        except SpotifyError as e:
            await progress.edit_text(
                t("error.track_failed", lang)
                + f"\n<code>{str(e)[:200]}</code>",
                parse_mode="HTML",
                reply_markup=get_back_keyboard(lang),
            )
            return
        except Exception as e:
            logger.exception("fetch упал: %s", canonical_url)
            await progress.edit_text(
                t("error.generic", lang, msg=str(e)[:300]),
                parse_mode="HTML",
                reply_markup=get_back_keyboard(lang),
            )
            return

        # ───── Отправка аудио в Telegram ─────
        try:
            await progress.edit_text(
                t("download.uploading", lang),
                parse_mode="HTML",
            )
        except Exception:
            pass

        try:
            sent = await message.answer_audio(
                FSInputFile(result.file_path),
                title=result.title,
                performer=result.artist or None,
                duration=result.duration or None,
            )
            if sent.audio:
                async with async_session() as session:
                    await save_download(
                        session,
                        spotify_url=track.url,
                        format_key=FORMAT_KEY,
                        file_id=sent.audio.file_id,
                        title=track.title,
                    )
                    await increment_download_count(session, user.id)
        except Exception as e:
            logger.exception("Не удалось отправить аудио")
            await progress.edit_text(
                t("error.generic", lang, msg=str(e)[:300]),
                parse_mode="HTML",
            )
            return

        try:
            await progress.delete()
        except Exception:
            pass

    finally:
        if result is not None:
            downloader.cleanup(result)


async def _get_lang(user_id: int) -> str:
    async with async_session() as session:
        return await get_user_language(session, user_id)
