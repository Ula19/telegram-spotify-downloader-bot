"""Оркестратор скачивания — перебирает провайдеров по цепочке с фоллбеком.

Контракт для хендлера:
    track, result = await downloader.fetch(url, on_metadata=cb)
    downloader.cleanup(result)

Цепочка провайдеров (по порядку) задаётся в _build_providers(). Пробуем каждого:
если провайдер упал сбоем (5xx/timeout/429/CDN) — идём к следующему. На отказ
"это не трек" (SpotifyNotSupported) фоллбек НЕ делаем. Если легли все — кидаем
SpotifyAllProvidersFailed и один раз дёргаем алерт админам.

Провайдеры (см. bot/services/providers/). Порядок выстроен по данным из прода:
семейство «24-7» (по 25/день) сверху, вечно-таймаутящий downloader9 — вниз.
    1. 24-7-mp3-fast                    GET  /download_track_m4a?url=  — {status,url}, m4a, oEmbed
    2. 24-7-premium                     GET  /download_track_m4a?url=  — {status,url}, m4a, oEmbed
    3. 24-7-tracks-albums               GET  /download_track_m4a?url=  — {status,url}, m4a, oEmbed
    4. spotify-downloader-v2            POST /v1/convert   (json url)  — 320kbps, без метадаты
    5. spotify-music-mp3-downloader-api GET  /download?link=          — богатая метадата
    6. spotify-downloader-mp33          POST /spotify.php  (form url=)
    7. spotify-downloader23             POST /spotify.php  (form url=)
    8. spotify-downloader9              GET  /downloadSong?songId=     — часто таймаутит
    9. spotdl                           self-hosted (YouTube)          — последний рубеж
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Awaitable, Callable

import httpx

from bot.services.providers.base import (
    BaseProvider,
    DownloadResult,
    SpotifyAllProvidersFailed,
    SpotifyAPIDown,
    SpotifyError,
    SpotifyNotSupported,
    SpotifyTimeout,
    TrackInfo,
    safe_unlink,
)
from bot.services.providers.rapidapi import (
    RapidAPIProvider,
    parse_downloader9,
    parse_medias,
    parse_medias_wrapped,
    parse_status_url,
    parse_v2,
)
from bot.services.providers.spotdl_provider import SpotdlProvider

logger = logging.getLogger(__name__)

# Реэкспорт для обратной совместимости — хендлер импортит эти имена отсюда
__all__ = [
    "TrackInfo",
    "DownloadResult",
    "SpotifyError",
    "SpotifyNotSupported",
    "SpotifyAPIDown",
    "SpotifyAllProvidersFailed",
    "SpotifyDownloader",
    "downloader",
]

# callback показа метадаты во время скачивания
OnMetadata = Callable[[TrackInfo], Awaitable[None]]


def _build_providers() -> list[BaseProvider]:
    """Собирает цепочку провайдеров в порядке приоритета."""
    # «24-7» конвертят синхронно — на незакэшированном треке ответ идёт >10с,
    # поэтому даём им больше времени. Backend у всех троих общий (один владелец):
    # group="24-7" → при таймауте одного оркестратор пропускает остальных.
    t247 = httpx.Timeout(20.0, connect=6.0)
    return [
        # Семейство «24-7» (один владелец, но у каждого свой лимит 25/день) —
        # ставим первыми, чтобы жечь их дешёвую квоту раньше остальных.
        RapidAPIProvider(
            name="24-7-mp3-fast",
            host="mp3-spotify-downloader-api-fast-24-7-api.p.rapidapi.com",
            path="/download_track_m4a",  # mp3-ссылка отдаёт 404, живой только m4a
            audio_ext=".m4a",
            method="GET",
            link_param="url",
            parser=parse_status_url,
            needs_oembed=True,
            timeout=t247,
            group="24-7",
        ),
        RapidAPIProvider(
            name="24-7-premium",
            host="spotify-downloader-mp3-m4a-flac-premium-api-stable-24-7.p.rapidapi.com",
            path="/download_track_m4a",  # mp3-ссылка отдаёт 404, живой только m4a
            audio_ext=".m4a",
            method="GET",
            link_param="url",
            parser=parse_status_url,
            needs_oembed=True,
            timeout=t247,
            group="24-7",
        ),
        RapidAPIProvider(
            name="24-7-tracks-albums",
            host="24-7-spotify-mp3-downloader-api-tracks-playlists-albums.p.rapidapi.com",
            path="/download_track_m4a",  # mp3-ссылка отдаёт 404, живой только m4a
            audio_ext=".m4a",
            method="GET",
            link_param="url",
            parser=parse_status_url,
            needs_oembed=True,
            timeout=t247,
            group="24-7",
        ),
        RapidAPIProvider(
            name="spotify-downloader-v2",
            host="spotify-downloader-v2.p.rapidapi.com",
            path="/v1/convert",
            method="POST",
            json_field="url",
            parser=parse_v2,
            needs_oembed=True,
        ),
        RapidAPIProvider(
            name="spotify-music-mp3-downloader-api",
            host="spotify-music-mp3-downloader-api.p.rapidapi.com",
            path="/download",
            method="GET",
            link_param="link",
            parser=parse_medias_wrapped,
        ),
        RapidAPIProvider(
            name="spotify-downloader-mp33",
            host="spotify-downloader-mp33.p.rapidapi.com",
            path="/spotify.php",
            method="POST",
            form_field="url",
            parser=parse_medias,
        ),
        RapidAPIProvider(
            name="spotify-downloader23",
            host="spotify-downloader23.p.rapidapi.com",
            path="/spotify.php",
            method="POST",
            form_field="url",
            parser=parse_medias,
        ),
        RapidAPIProvider(
            name="spotify-downloader9",
            host="spotify-downloader9.p.rapidapi.com",
            path="/downloadSong",
            method="GET",
            link_param="songId",
            parser=parse_downloader9,
        ),
        SpotdlProvider(),
    ]


class SpotifyDownloader:
    """Держит цепочку провайдеров и добывает трек, перебирая их по очереди."""

    def __init__(self) -> None:
        self.providers = _build_providers()
        # callback алертов админам: (source, msg) -> None
        self.on_source_failed: Callable[[str, str], None] | None = None

    async def fetch(
        self,
        url: str,
        on_metadata: OnMetadata | None = None,
    ) -> tuple[TrackInfo, DownloadResult]:
        """Добывает трек через первого сработавшего провайдера.

        on_metadata (если задан) вызывается один раз, как только получены
        метаданные — чтобы показать юзеру название, пока идёт скачивание.
        """
        from bot.utils.helpers import parse_spotify_url

        parsed = parse_spotify_url(url)
        if not parsed:
            raise SpotifyError("Невалидный URL Spotify")
        kind, track_id = parsed
        if kind != "track":
            raise SpotifyNotSupported("Сейчас поддерживаются только одиночные треки")

        canonical_url = f"https://open.spotify.com/track/{track_id}"

        errors: list[tuple[str, str]] = []
        metadata_shown = False
        dead_groups: set[str] = set()  # backend группы завис — остальных из неё пропускаем

        for provider in self.providers:
            group = getattr(provider, "group", None)
            if group and group in dead_groups:
                logger.info(
                    "Провайдер '%s' пропущен: backend группы '%s' уже завис",
                    provider.name, group,
                )
                continue
            try:
                track = await provider.get_track(url, track_id, canonical_url)

                if on_metadata and not metadata_shown:
                    metadata_shown = True
                    try:
                        await on_metadata(track)
                    except Exception:  # показ метадаты не должен ронять скачивание
                        logger.debug("on_metadata callback упал", exc_info=True)

                result = await provider.download_track(track)
                logger.info("Трек добыт через провайдера '%s'", provider.name)
                return track, result

            except SpotifyNotSupported:
                raise  # осмысленный отказ — фоллбек не нужен
            except SpotifyError as e:  # сюда же попадает SpotifyAPIDown
                errors.append((provider.name, str(e)))
                logger.warning(
                    "Провайдер '%s' не смог (%s): %s",
                    provider.name, type(e).__name__, e,
                )
                # таймаут провайдера с общим backend → остальных из группы не мучаем
                if isinstance(e, SpotifyTimeout) and group:
                    dead_groups.add(group)
                continue
            except Exception as e:  # неожиданное — тоже пробуем следующего
                errors.append((provider.name, str(e)))
                logger.exception("Провайдер '%s' упал неожиданно", provider.name)
                continue

        # сюда дошли — значит легли все
        summary = "; ".join(f"{n}: {m}" for n, m in errors)
        self._report_source_failure("all", f"легли все провайдеры → {summary}"[:500])
        raise SpotifyAllProvidersFailed(errors)

    def cleanup(self, result: DownloadResult) -> None:
        """Удаляет временный mp3 с диска."""
        safe_unlink(Path(result.file_path))

    def _report_source_failure(self, source: str, msg: str) -> None:
        """Пинает callback алертов (если подключён)."""
        if self.on_source_failed is None:
            return
        try:
            self.on_source_failed(source, msg)
        except Exception:
            logger.exception("on_source_failed callback упал")

    async def close(self) -> None:
        """Закрывает http-клиенты всех провайдеров при остановке бота."""
        for provider in self.providers:
            try:
                await provider.close()
            except Exception:
                logger.debug("Ошибка закрытия провайдера %s", provider.name, exc_info=True)


# Глобальный экземпляр — используется из handlers/download.py
downloader = SpotifyDownloader()
