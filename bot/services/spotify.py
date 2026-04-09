"""Сервис скачивания треков Spotify через RapidAPI (spotify-downloader9).

Контракт:
    await downloader.get_track(url)       -> TrackInfo
    await downloader.download_track(track) -> DownloadResult
    downloader.cleanup(result)

Провайдер: Spotify Music MP3 Downloader API на RapidAPI.
    GET https://spotify-music-mp3-downloader-api.p.rapidapi.com/download
    Query:   link=<spotify_track_url>
    Headers:
        X-RapidAPI-Key:  <RAPIDAPI_KEY>
        X-RapidAPI-Host: spotify-music-mp3-downloader-api.p.rapidapi.com

Формат ответа (реальный, проверен 2026-04-09):
    {
      "success": true,
      "message": "success",
      "data": {
        "url": "https://open.spotify.com/track/<id>",
        "title": "...",
        "author": "Artist1, Artist2",
        "thumbnail": "https://.../cover.jpg",
        "duration": "4:08",          // строка M:SS или H:MM:SS
        "track_id": "<id>",
        "medias": [
          {"url": "https://cdn.../file.mp3", "quality": "HQ",
           "extension": "mp3", "type": "audio"}
        ],
        "type": "single",
        "error": false
      }
    }
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import httpx

from bot.config import settings

logger = logging.getLogger(__name__)

# Папка для временных mp3 (монтируется из docker-compose)
TMP_DIR = Path("/tmp/spotify_bot")
TMP_DIR.mkdir(parents=True, exist_ok=True)

# Провайдер RapidAPI — Spotify Music MP3 Downloader API
RAPIDAPI_HOST = "spotify-music-mp3-downloader-api.p.rapidapi.com"
RAPIDAPI_BASE = f"https://{RAPIDAPI_HOST}"

# Таймауты
API_TIMEOUT = httpx.Timeout(30.0, connect=10.0)     # запрос к RapidAPI
DOWNLOAD_TIMEOUT = httpx.Timeout(120.0, connect=10.0)  # скачивание mp3 файла

# Семафор на одновременные скачивания (бережём квоту и не душим провайдера)
_DOWNLOAD_SEMAPHORE = asyncio.Semaphore(3)


# ───────────────────────────── DTO ───────────────────────────── #

@dataclass
class TrackInfo:
    url: str                              # каноничный https://open.spotify.com/track/<id>
    track_id: str
    title: str
    artists: list[str] = field(default_factory=list)
    album: str = ""
    duration: int = 0                     # секунды
    cover_url: str | None = None

    @property
    def artist_line(self) -> str:
        return ", ".join(self.artists) if self.artists else ""


@dataclass
class DownloadResult:
    file_path: str
    title: str
    artist: str
    duration: int


class SpotifyError(Exception):
    """Базовая ошибка сервиса."""


class SpotifyNotSupported(SpotifyError):
    """Ссылка на episode/show/album/playlist — сейчас не поддерживается."""


class SpotifyAPIDown(SpotifyError):
    """RapidAPI провайдер недоступен (5xx / timeout / 429)."""


# ───────────────────────── Основной класс ────────────────────── #

class SpotifyDownloader:
    """Тонкий HTTP-клиент к RapidAPI spotify-downloader9."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._client_lock = asyncio.Lock()
        self.on_source_failed: Callable[[str, str], None] | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Ленивая инициализация httpx клиента."""
        if self._client is not None:
            return self._client
        async with self._client_lock:
            if self._client is None:
                self._client = httpx.AsyncClient(
                    timeout=API_TIMEOUT,
                    follow_redirects=True,
                    headers=self._build_headers(),
                    proxy=settings.proxy_url or None,
                )
            return self._client

    def _build_headers(self) -> dict[str, str]:
        if not settings.rapidapi_key:
            raise SpotifyError(
                "RAPIDAPI_KEY не задан в .env — бот не сможет качать треки"
            )
        return {
            "X-RapidAPI-Key": settings.rapidapi_key,
            "X-RapidAPI-Host": RAPIDAPI_HOST,
            "Accept": "application/json",
            "User-Agent": "bot_4_spotify/1.0",
        }

    # ───── получение метаданных трека ───── #

    async def get_track(self, url: str) -> TrackInfo:
        """Получает метаданные трека по Spotify URL."""
        from bot.utils.helpers import parse_spotify_url

        parsed = parse_spotify_url(url)
        if not parsed:
            raise SpotifyError("Невалидный URL Spotify")
        kind, track_id = parsed
        if kind != "track":
            # Для album/playlist сейчас не поддерживаем
            raise SpotifyNotSupported(
                "Сейчас поддерживаются только одиночные треки"
            )

        # Запрашиваем provider — заодно получаем и метаданные, и downloadLink
        payload = await self._call_download_endpoint(track_id)

        return self._parse_track_response(
            payload=payload,
            track_id=track_id,
            canonical_url=f"https://open.spotify.com/track/{track_id}",
        )

    async def _call_download_endpoint(self, track_id: str) -> dict[str, Any]:
        """Вызов GET /download?link=<spotify_url> с обработкой ошибок."""
        client = await self._get_client()
        spotify_url = f"https://open.spotify.com/track/{track_id}"
        try:
            response = await client.get(
                f"{RAPIDAPI_BASE}/download",
                params={"link": spotify_url},
            )
        except httpx.TimeoutException as e:
            self._report_source_failure("timeout", str(e))
            raise SpotifyAPIDown("Таймаут RapidAPI") from e
        except httpx.HTTPError as e:
            self._report_source_failure("network", str(e))
            raise SpotifyAPIDown(f"Сеть: {e}") from e

        if response.status_code == 401:
            raise SpotifyError("RapidAPI: неверный RAPIDAPI_KEY (401)")
        if response.status_code == 403:
            raise SpotifyError(
                "RapidAPI: нет подписки на spotify-downloader9 (403)"
            )
        if response.status_code == 429:
            self._report_source_failure("quota", "429 rate limit")
            raise SpotifyAPIDown("RapidAPI: превышен лимит запросов (429)")
        if response.status_code >= 500:
            self._report_source_failure("server", f"{response.status_code}")
            raise SpotifyAPIDown(f"RapidAPI {response.status_code}")
        if response.status_code >= 400:
            raise SpotifyError(
                f"RapidAPI вернул {response.status_code}: "
                f"{response.text[:200]}"
            )

        try:
            payload = response.json()
        except Exception as e:
            raise SpotifyError(f"RapidAPI вернул не-JSON: {e}") from e

        return payload

    def _parse_track_response(
        self,
        payload: dict[str, Any],
        track_id: str,
        canonical_url: str,
    ) -> TrackInfo:
        """Достаёт поля из JSON-ответа Spotify Music MP3 Downloader API.

        Если провайдер сменит формат — правь только эту функцию.
        """
        if not payload or not isinstance(payload, dict):
            raise SpotifyError("Пустой ответ RapidAPI")

        # В верхнем уровне: success/message/data
        if payload.get("success") is False or payload.get("error") is True:
            msg = payload.get("message") or "API вернул ошибку"
            raise SpotifyError(f"RapidAPI: {msg}")

        data = payload.get("data")
        if not isinstance(data, dict):
            raise SpotifyError("Неожиданная структура ответа RapidAPI (нет data)")

        title = data.get("title") or "Unknown"
        artists = self._normalize_artists(
            data.get("author") or data.get("artist") or data.get("artists") or ""
        )
        # у этого провайдера нет поля album — оставим пустым
        album = data.get("album") or ""
        cover = data.get("thumbnail") or data.get("cover")

        # duration у этого провайдера — строка "M:SS" или "H:MM:SS"
        duration = self._parse_duration(data.get("duration"))

        # Прямая ссылка на mp3 лежит в medias[0].url
        medias = data.get("medias") or []
        if not medias or not isinstance(medias, list):
            raise SpotifyError("В ответе нет массива medias")

        # Выбираем первый audio/mp3 — обычно он один
        download_link: str | None = None
        for media in medias:
            if not isinstance(media, dict):
                continue
            if media.get("type") == "audio" or media.get("extension") == "mp3":
                download_link = media.get("url")
                if download_link:
                    break
        if not download_link and isinstance(medias[0], dict):
            download_link = medias[0].get("url")

        if not download_link:
            raise SpotifyError("В medias нет ссылки на mp3")

        track = TrackInfo(
            url=canonical_url,
            track_id=track_id,
            title=title,
            artists=artists,
            album=album,
            duration=duration,
            cover_url=cover,
        )
        # Прячем downloadLink в _download_url — доступно в download_track
        track._download_url = download_link  # type: ignore[attr-defined]
        return track

    @staticmethod
    def _parse_duration(raw: Any) -> int:
        """Парсит длительность. Принимает 'M:SS', 'H:MM:SS', int секунд, int миллисекунд."""
        if raw is None or raw == "":
            return 0
        if isinstance(raw, (int, float)):
            value = int(raw)
            # если выглядит как мс (> 10 минут треков не бывает в сек * 1000 > 1e6)
            return value // 1000 if value > 10_000 else value
        if isinstance(raw, str):
            parts = raw.split(":")
            try:
                nums = [int(p) for p in parts]
            except ValueError:
                return 0
            if len(nums) == 2:
                return nums[0] * 60 + nums[1]
            if len(nums) == 3:
                return nums[0] * 3600 + nums[1] * 60 + nums[2]
            if len(nums) == 1:
                return nums[0]
        return 0

    @staticmethod
    def _normalize_artists(raw: Any) -> list[str]:
        if not raw:
            return []
        if isinstance(raw, str):
            # "Artist1, Artist2" или "Artist1 & Artist2"
            return [
                a.strip()
                for a in raw.replace("&", ",").split(",")
                if a.strip()
            ]
        if isinstance(raw, list):
            result: list[str] = []
            for item in raw:
                if isinstance(item, str):
                    result.append(item.strip())
                elif isinstance(item, dict):
                    name = item.get("name") or item.get("title")
                    if name:
                        result.append(str(name).strip())
            return result
        return []

    # ───── скачивание mp3 файла ───── #

    async def download_track(self, track: TrackInfo) -> DownloadResult:
        """Качает mp3 файл по прямой ссылке из TrackInfo в /tmp/spotify_bot/."""
        download_url: str | None = getattr(track, "_download_url", None)
        if not download_url:
            raise SpotifyError(
                "download_track без предварительного get_track — нет прямой ссылки"
            )

        async with _DOWNLOAD_SEMAPHORE:
            dst = TMP_DIR / f"{uuid.uuid4().hex}.mp3"
            client = await self._get_client()
            try:
                # Для CDN ссылки обычно RapidAPI заголовки не нужны,
                # но лишними не будут
                async with client.stream(
                    "GET",
                    download_url,
                    timeout=DOWNLOAD_TIMEOUT,
                ) as response:
                    if response.status_code >= 400:
                        self._report_source_failure(
                            "cdn", f"{response.status_code}"
                        )
                        raise SpotifyAPIDown(
                            f"CDN вернул {response.status_code}"
                        )
                    with dst.open("wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
                            f.write(chunk)
            except httpx.TimeoutException as e:
                self._safe_unlink(dst)
                self._report_source_failure("cdn_timeout", str(e))
                raise SpotifyAPIDown("Таймаут при скачивании mp3") from e
            except httpx.HTTPError as e:
                self._safe_unlink(dst)
                raise SpotifyError(f"Ошибка скачивания: {e}") from e
            except Exception:
                self._safe_unlink(dst)
                raise

        if not dst.exists() or dst.stat().st_size == 0:
            self._safe_unlink(dst)
            raise SpotifyError("Скачан пустой файл")

        return DownloadResult(
            file_path=str(dst),
            title=track.title,
            artist=track.artist_line,
            duration=track.duration,
        )

    def cleanup(self, result: DownloadResult) -> None:
        """Удаляет временный mp3 с диска."""
        self._safe_unlink(Path(result.file_path))

    @staticmethod
    def _safe_unlink(path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except OSError as e:
            logger.warning("Не удалось удалить %s: %s", path, e)

    def _report_source_failure(self, category: str, msg: str) -> None:
        """Пинает callback алертов (если подключён)."""
        if self.on_source_failed is None:
            return
        try:
            self.on_source_failed("rapidapi", f"[{category}] {msg}")
        except Exception:
            logger.exception("on_source_failed callback упал")

    async def close(self) -> None:
        """Закрывает httpx клиент при остановке бота."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


# Глобальный экземпляр — используется из handlers/download.py
downloader = SpotifyDownloader()
