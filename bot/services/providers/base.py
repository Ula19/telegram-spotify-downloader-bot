"""Базовый слой провайдеров: DTO, исключения, общий скачиватель файла.

Тут лежит всё, что переиспользуют все провайдеры, чтобы не копипастить.
"""
from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Папка для временных mp3 (монтируется из docker-compose)
TMP_DIR = Path("/tmp/spotify_bot")
TMP_DIR.mkdir(parents=True, exist_ok=True)

# Таймаут на скачивание самого mp3-файла с CDN
DOWNLOAD_TIMEOUT = httpx.Timeout(120.0, connect=10.0)


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
    download_url: str | None = None       # прямая ссылка на mp3 (если провайдер её отдал)
    provider: str = ""                    # имя провайдера, который отдал трек

    @property
    def artist_line(self) -> str:
        return ", ".join(self.artists) if self.artists else ""


@dataclass
class DownloadResult:
    file_path: str
    title: str
    artist: str
    duration: int


# ───────────────────────── Исключения ────────────────────────── #

class SpotifyError(Exception):
    """Базовая ошибка сервиса."""


class SpotifyNotSupported(SpotifyError):
    """Ссылка на episode/show/album/playlist — сейчас не поддерживается.

    На неё цепочка НЕ фоллбечится (это осмысленный отказ, а не сбой).
    """


class SpotifyAPIDown(SpotifyError):
    """Провайдер недоступен (5xx / timeout / 429 / ошибка CDN) — можно пробовать следующий."""


class SpotifyTimeout(SpotifyAPIDown):
    """Провайдер не ответил за таймаут. Сигнал, что его backend завис —
    для провайдеров с общим backend (group) остальных из группы пропускаем."""


class SpotifyAllProvidersFailed(SpotifyAPIDown):
    """Легли вообще все провайдеры в цепочке."""

    def __init__(self, errors: list[tuple[str, str]]) -> None:
        self.errors = errors
        detail = "; ".join(f"{name}: {msg}" for name, msg in errors) or "нет провайдеров"
        super().__init__(f"Все провайдеры недоступны ({detail})")


# ───────────────────────── Базовый класс ─────────────────────── #

class BaseProvider(ABC):
    """Контракт одного провайдера скачивания."""

    name: str = "base"

    @abstractmethod
    async def get_track(self, url: str, track_id: str, canonical_url: str) -> TrackInfo:
        """Достаёт метаданные трека (+ прямую ссылку, если провайдер её даёт)."""

    @abstractmethod
    async def download_track(self, track: TrackInfo) -> DownloadResult:
        """Качает mp3 в /tmp/spotify_bot и возвращает путь к файлу."""

    async def close(self) -> None:
        """Закрывает ресурсы (httpx-клиент и т.п.) при остановке бота."""


# ───────────────────────── Общие хелперы ─────────────────────── #

def safe_unlink(path: Path) -> None:
    """Удаляет файл, молча проглатывая ошибки."""
    try:
        if path.exists():
            path.unlink()
    except OSError as e:
        logger.warning("Не удалось удалить %s: %s", path, e)


async def stream_to_file(
    client: httpx.AsyncClient,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout = DOWNLOAD_TIMEOUT,
    suffix: str = ".mp3",
) -> Path:
    """Стримит аудио по прямой ссылке в уникальный файл. Используют все RapidAPI-провайдеры.

    suffix — расширение файла (.mp3 / .m4a): Telegram определяет формат по нему.
    """
    dst = TMP_DIR / f"{uuid.uuid4().hex}{suffix}"
    try:
        async with client.stream("GET", url, headers=headers, timeout=timeout) as response:
            if response.status_code >= 400:
                raise SpotifyAPIDown(f"CDN вернул {response.status_code}")
            with dst.open("wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
                    f.write(chunk)
    except httpx.TimeoutException as e:
        safe_unlink(dst)
        raise SpotifyAPIDown("Таймаут при скачивании mp3") from e
    except httpx.HTTPError as e:
        safe_unlink(dst)
        raise SpotifyError(f"Ошибка скачивания: {e}") from e
    except Exception:
        safe_unlink(dst)
        raise

    if not dst.exists() or dst.stat().st_size == 0:
        safe_unlink(dst)
        raise SpotifyError("Скачан пустой файл")

    return dst
