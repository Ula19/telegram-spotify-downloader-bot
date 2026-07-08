"""spotdl — последний рубеж цепочки. Качает аудио с YouTube через yt-dlp.

Работает без RapidAPI и без квот, но тяжелее (ffmpeg) и медленнее, поэтому
стоит в самом конце и включается, только когда легли все RapidAPI-провайдеры.
Запускаем spotdl как отдельный процесс (asyncio subprocess).
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import uuid

import httpx

from bot.config import settings

from .base import (
    TMP_DIR,
    BaseProvider,
    DownloadResult,
    SpotifyAPIDown,
    SpotifyError,
    TrackInfo,
    safe_unlink,
)
from .metadata import fetch_oembed

logger = logging.getLogger(__name__)

# spotdl тяжёлый — не даём запускать больше одного за раз, бережём слабый сервер
_SPOTDL_SEMAPHORE = asyncio.Semaphore(1)

# Максимум на одну загрузку через spotdl (мэтчинг + скачивание + конвертация)
SPOTDL_TIMEOUT = 180.0


class SpotdlProvider(BaseProvider):
    """Качает трек через CLI spotdl."""

    name = "spotdl"

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                follow_redirects=True,
                proxy=settings.proxy_url or None,  # oEmbed тоже через прокси, если задан
            )
        return self._client

    async def get_track(self, url: str, track_id: str, canonical_url: str) -> TrackInfo:
        # spotdl не отдаёт метадату дёшево — берём название/обложку из oEmbed.
        # Если oEmbed недоступен — не страшно, качаем с title="Unknown".
        title, cover = "Unknown", None
        try:
            meta = await fetch_oembed(self._get_client(), canonical_url)
            title = meta.get("title") or "Unknown"
            cover = meta.get("thumbnail_url")
        except Exception:
            logger.debug("spotdl: не удалось добрать метадату oEmbed", exc_info=True)

        return TrackInfo(
            url=canonical_url,
            track_id=track_id,
            title=title,
            artists=[],
            album="",
            duration=0,
            cover_url=cover,
            download_url=None,
            provider=self.name,
        )

    async def download_track(self, track: TrackInfo) -> DownloadResult:
        if shutil.which("spotdl") is None:
            raise SpotifyError("spotdl не установлен в системе")

        # уникальный префикс, чтобы параллельные загрузки не перезаписали друг друга
        prefix = uuid.uuid4().hex[:8]
        out_template = str(TMP_DIR / f"{prefix}-") + "{track-id}.{output-ext}"

        cmd = [
            "spotdl", "download", track.url,
            "--output", out_template,
            "--format", "mp3",
        ]

        # Прокси. Тонкость: штатный --proxy у spotdl принимает ТОЛЬКО http(s),
        # на socks5 он падает ("Invalid proxy server"). Поэтому socks отдаём
        # напрямую yt-dlp через --yt-dlp-args (он socks умеет). А поиск через
        # yt-dlp есть только у провайдера youtube — его и выбираем для socks.
        proxy = (settings.proxy_url or "").strip()
        if proxy.startswith(("http://", "https://")):
            cmd += ["--audio", "youtube-music", "youtube", "--proxy", proxy]
        elif proxy.startswith(("socks5://", "socks5h://", "socks4://", "socks://")):
            cmd += ["--audio", "youtube", "--yt-dlp-args", f"--proxy {proxy}"]
        else:
            # без прокси; bandcamp не берём — он даёт кривые матчи
            cmd += ["--audio", "youtube-music", "youtube"]

        # cookie-файл (опц.) — обход "Sign in to confirm you're not a bot"
        if settings.spotdl_cookie_file:
            cmd += ["--cookie-file", settings.spotdl_cookie_file]

        # если заданы ключи Spotify API — spotdl мэтчит точнее
        if settings.spotify_client_id and settings.spotify_client_secret:
            cmd += [
                "--client-id", settings.spotify_client_id,
                "--client-secret", settings.spotify_client_secret,
            ]

        async with _SPOTDL_SEMAPHORE:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            try:
                stdout, _ = await asyncio.wait_for(
                    proc.communicate(), timeout=SPOTDL_TIMEOUT
                )
            except asyncio.TimeoutError as e:
                proc.kill()
                await proc.wait()
                raise SpotifyAPIDown("spotdl: таймаут") from e

        if proc.returncode != 0:
            tail = (stdout or b"").decode(errors="ignore")[-300:]
            raise SpotifyAPIDown(f"spotdl: код {proc.returncode} ({tail})")

        # ищем созданный файл по нашему префиксу.
        # ВАЖНО: spotdl выходит с кодом 0 даже когда ничего не скачал
        # (например, YouTube заблочен) — поэтому проверяем наличие файла.
        files = sorted(TMP_DIR.glob(f"{prefix}-*.mp3"))
        if not files:
            tail = (stdout or b"").decode(errors="ignore").strip()[-200:]
            raise SpotifyAPIDown(f"spotdl не скачал трек ({tail})")
        # если вдруг создалось несколько — лишние удаляем, берём первый
        for extra in files[1:]:
            safe_unlink(extra)

        return DownloadResult(
            file_path=str(files[0]),
            title=track.title,
            artist=track.artist_line,
            duration=track.duration,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
