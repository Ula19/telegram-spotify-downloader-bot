"""Параметризованный провайдер RapidAPI + парсеры под разные форматы ответа.

Один класс RapidAPIProvider умеет любой RapidAPI-эндпоинт: настраиваем метод
(GET/POST), способ передачи ссылки (query-параметр / form-поле / json-поле) и
функцию-парсер. Чтобы добавить новый движок — достаточно ещё одного инстанса.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

import httpx

from bot.config import settings

from .base import (
    BaseProvider,
    DownloadResult,
    SpotifyAPIDown,
    SpotifyError,
    SpotifyTimeout,
    TrackInfo,
    stream_to_file,
)
from .metadata import fetch_oembed

logger = logging.getLogger(__name__)

# Короткий таймаут на API-запрос — фейл-фаст, чтобы цепочка быстро шла дальше.
# 10с достаточно живому движку; мёртвый (downloader9 вечно таймаутит) проскочим быстрее.
API_TIMEOUT = httpx.Timeout(10.0, connect=6.0)

# Тип парсера: (json-ответ, track_id, каноничный_url) -> TrackInfo
Parser = Callable[[dict, str, str], TrackInfo]


# ───────────────────────── Хелперы парсинга ──────────────────── #

def normalize_artists(raw: Any) -> list[str]:
    """Приводит артистов к list[str] из строки 'A, B & C' или списка."""
    if not raw:
        return []
    if isinstance(raw, str):
        return [a.strip() for a in raw.replace("&", ",").split(",") if a.strip()]
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


def parse_duration(raw: Any) -> int:
    """Парсит длительность: 'M:SS', 'H:MM:SS', int секунд или int миллисекунд."""
    if raw is None or raw == "":
        return 0
    if isinstance(raw, (int, float)):
        value = int(raw)
        # если число большое — вероятно это миллисекунды
        return value // 1000 if value > 10_000 else value
    if isinstance(raw, str):
        try:
            nums = [int(p) for p in raw.split(":")]
        except ValueError:
            return 0
        if len(nums) == 3:
            return nums[0] * 3600 + nums[1] * 60 + nums[2]
        if len(nums) == 2:
            return nums[0] * 60 + nums[1]
        if len(nums) == 1:
            return nums[0]
    return 0


def _pick_audio_url(medias: Any) -> str | None:
    """Достаёт ссылку на аудио из массива medias."""
    if not isinstance(medias, list) or not medias:
        return None
    for media in medias:
        if not isinstance(media, dict):
            continue
        if media.get("type") == "audio" or media.get("extension") == "mp3":
            if media.get("url"):
                return media["url"]
    # запасной вариант — первый элемент
    first = medias[0]
    return first.get("url") if isinstance(first, dict) else None


# ───────────────────────── Парсеры форматов ──────────────────── #

def parse_downloader9(payload: dict, track_id: str, canonical_url: str) -> TrackInfo:
    """spotify-downloader9: {success, data:{artist,title,album,cover,downloadLink}}."""
    if not isinstance(payload, dict):
        raise SpotifyError("пустой ответ")
    if payload.get("success") is False:
        raise SpotifyError(payload.get("message") or "API вернул ошибку")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise SpotifyError("нет data в ответе")
    download_url = data.get("downloadLink")
    if not download_url:
        raise SpotifyError("нет downloadLink")
    return TrackInfo(
        url=canonical_url,
        track_id=track_id,
        title=data.get("title") or "Unknown",
        artists=normalize_artists(data.get("artist") or data.get("author")),
        album=data.get("album") or "",
        duration=parse_duration(data.get("duration")),
        cover_url=data.get("cover") or data.get("thumbnail"),
        download_url=download_url,
    )


def parse_medias(payload: dict, track_id: str, canonical_url: str) -> TrackInfo:
    """Формат с массивом medias на верхнем уровне (mp33, downloader23)."""
    return _parse_medias_root(payload, payload, track_id, canonical_url)


def parse_medias_wrapped(payload: dict, track_id: str, canonical_url: str) -> TrackInfo:
    """Тот же формат, но обёрнутый в {success, data:{...medias...}} (текущий движок)."""
    if not isinstance(payload, dict):
        raise SpotifyError("пустой ответ")
    if payload.get("success") is False:
        raise SpotifyError(payload.get("message") or "API вернул ошибку")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise SpotifyError("нет data в ответе")
    return _parse_medias_root(payload, data, track_id, canonical_url)


def _parse_medias_root(payload: dict, root: dict, track_id: str, canonical_url: str) -> TrackInfo:
    """Общая логика для medias-формата: root — где лежат title/author/medias."""
    if not isinstance(root, dict):
        raise SpotifyError("нет данных в ответе")
    if root.get("error") is True:
        raise SpotifyError(payload.get("message") or root.get("message") or "API вернул ошибку")
    download_url = _pick_audio_url(root.get("medias"))
    if not download_url:
        raise SpotifyError("нет ссылки в medias")
    return TrackInfo(
        url=canonical_url,
        track_id=track_id,
        title=root.get("title") or "Unknown",
        artists=normalize_artists(root.get("author") or root.get("artist") or root.get("artists")),
        album=root.get("album") or "",
        duration=parse_duration(root.get("duration")),
        cover_url=root.get("thumbnail") or root.get("cover"),
        download_url=download_url,
    )


def parse_status_url(payload: dict, track_id: str, canonical_url: str) -> TrackInfo:
    """Формат семейства «24-7»: {status:'done', url:'<файл>', ...} — метадаты нет.

    Ссылку берём из url. Если статус говорит «ещё готовится» (processing/pending)
    и ссылки нет — считаем сбоем, цепочка идёт дальше (опрос не делаем).
    """
    if not isinstance(payload, dict):
        raise SpotifyError("пустой ответ")
    if payload.get("error"):
        raise SpotifyError(str(payload.get("error") or payload.get("message") or "ошибка API"))
    status = str(payload.get("status") or "").lower()
    download_url = payload.get("url") or payload.get("download_url") or payload.get("link")
    ready = {"done", "ok", "success", "finished", "completed", "ready"}
    if not download_url:
        if status and status not in ready:
            raise SpotifyAPIDown(f"трек ещё не готов (status={status})")
        raise SpotifyError("нет url в ответе")
    return TrackInfo(
        url=canonical_url,
        track_id=track_id,
        title="",  # метадату добирает RapidAPIProvider через oEmbed (needs_oembed=True)
        artists=[],
        album="",
        duration=0,
        cover_url=None,
        download_url=download_url,
    )


def parse_v2(payload: dict, track_id: str, canonical_url: str) -> TrackInfo:
    """spotify-downloader-v2: {spotify_id, download_url, ...} — метадаты нет."""
    if not isinstance(payload, dict):
        raise SpotifyError("пустой ответ")
    download_url = payload.get("download_url")
    if not download_url:
        raise SpotifyError("нет download_url")
    # title/artist пустые — RapidAPIProvider доберёт их через oEmbed (needs_oembed=True)
    return TrackInfo(
        url=canonical_url,
        track_id=track_id,
        title="",
        artists=[],
        album="",
        duration=0,
        cover_url=None,
        download_url=download_url,
    )


# ───────────────────────── Сам провайдер ─────────────────────── #

class RapidAPIProvider(BaseProvider):
    """Один RapidAPI-эндпоинт. Способ запроса и парсер задаются в конструкторе."""

    def __init__(
        self,
        *,
        name: str,
        host: str,
        path: str,
        parser: Parser,
        method: str = "GET",
        link_param: str | None = None,   # имя query-параметра для GET (?link=..)
        form_field: str | None = None,   # поле x-www-form-urlencoded для POST
        json_field: str | None = None,   # поле json-тела для POST
        needs_oembed: bool = False,      # добрать title/обложку через oEmbed
        timeout: httpx.Timeout | None = None,  # свой таймаут (медленным-синхронным нужен больше)
        group: str | None = None,        # общий backend: при таймауте одного пропускаем всю группу
        audio_ext: str = ".mp3",         # расширение отдаваемого файла (.mp3 / .m4a)
    ) -> None:
        self.name = name
        self.host = host
        self.path = path
        self.parser = parser
        self.method = method.upper()
        self.link_param = link_param
        self.form_field = form_field
        self.json_field = json_field
        self.needs_oembed = needs_oembed
        self.timeout = timeout or API_TIMEOUT
        self.group = group
        self.audio_ext = audio_ext
        self._client: httpx.AsyncClient | None = None

    @property
    def _base_url(self) -> str:
        return f"https://{self.host}{self.path}"

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            if not settings.rapidapi_key:
                raise SpotifyError("RAPIDAPI_KEY не задан в .env")
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                proxy=settings.proxy_url or None,  # поддержка SOCKS5/HTTP прокси
                headers={
                    "X-RapidAPI-Key": settings.rapidapi_key,
                    "X-RapidAPI-Host": self.host,
                    "Accept": "application/json",
                    "User-Agent": "bot_4_spotify/1.0",
                },
            )
        return self._client

    async def get_track(self, url: str, track_id: str, canonical_url: str) -> TrackInfo:
        payload = await self._call(canonical_url)
        track = self.parser(payload, track_id, canonical_url)
        track.provider = self.name
        if self.needs_oembed and not track.title:
            await self._backfill_metadata(track, canonical_url)
        return track

    async def _backfill_metadata(self, track: TrackInfo, canonical_url: str) -> None:
        """Добирает название/обложку через oEmbed, если провайдер их не дал."""
        meta = await fetch_oembed(self._get_client(), canonical_url)
        track.title = meta.get("title") or track.title or "Unknown"
        if not track.cover_url:
            track.cover_url = meta.get("thumbnail_url")

    async def _call(self, spotify_url: str) -> dict:
        """Делает запрос к RapidAPI и возвращает распарсенный JSON."""
        client = self._get_client()
        try:
            if self.method == "GET":
                resp = await client.get(self._base_url, params={self.link_param: spotify_url})
            elif self.form_field:
                resp = await client.post(self._base_url, data={self.form_field: spotify_url})
            else:
                resp = await client.post(self._base_url, json={self.json_field: spotify_url})
        except httpx.TimeoutException as e:
            raise SpotifyTimeout(f"{self.name}: таймаут") from e
        except httpx.HTTPError as e:
            raise SpotifyAPIDown(f"{self.name}: сеть {e}") from e

        self._check_status(resp)

        try:
            return resp.json()
        except Exception as e:
            raise SpotifyError(f"{self.name}: не-JSON ответ ({e})") from e

    def _check_status(self, resp: httpx.Response) -> None:
        code = resp.status_code
        if code == 401:
            raise SpotifyError(f"{self.name}: неверный RAPIDAPI_KEY (401)")
        if code == 403:
            raise SpotifyError(f"{self.name}: нет подписки на API (403)")
        if code == 429:
            raise SpotifyAPIDown(f"{self.name}: лимит запросов (429)")
        if code >= 500:
            raise SpotifyAPIDown(f"{self.name}: сервер {code}")
        if code >= 400:
            raise SpotifyError(f"{self.name}: {code} {resp.text[:150]}")

    async def download_track(self, track: TrackInfo) -> DownloadResult:
        if not track.download_url:
            raise SpotifyError(f"{self.name}: нет прямой ссылки на аудио")
        dst = await stream_to_file(
            self._get_client(), track.download_url, suffix=self.audio_ext
        )
        return DownloadResult(
            file_path=str(dst),
            title=track.title,
            artist=track.artist_line,
            duration=track.duration,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
