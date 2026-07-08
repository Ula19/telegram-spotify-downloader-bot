"""Добор метаданных трека через публичный Spotify oEmbed (без авторизации).

Нужен провайдерам, которые отдают только ссылку на mp3, но не название
(например spotify-downloader-v2 и spotdl). oEmbed даёт название и обложку.
Артиста oEmbed надёжно не отдаёт — оставляем пустым.
"""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_OEMBED_URL = "https://open.spotify.com/oembed"
_OEMBED_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def fetch_oembed(client: httpx.AsyncClient, spotify_url: str) -> dict:
    """Возвращает {title, thumbnail_url, ...} или пустой dict, если не вышло."""
    try:
        resp = await client.get(
            _OEMBED_URL,
            params={"url": spotify_url},
            timeout=_OEMBED_TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                return data
    except Exception as e:  # oEmbed — не критичный путь, молча падаем в пустоту
        logger.debug("oEmbed не ответил для %s: %s", spotify_url, e)
    return {}
