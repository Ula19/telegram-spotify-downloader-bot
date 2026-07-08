"""Хелперы для работы со ссылками Spotify"""
import re
from typing import Literal

SpotifyKind = Literal["track", "album", "playlist"]

# Spotify-айди — ровно 22 символа base62. Меньше/больше = мусор
# (ловим кривые ссылки вроде /track/BillieEilish, чтобы не гонять их по цепочке).
_ID = r"[a-zA-Z0-9]{22}(?![a-zA-Z0-9])"

# open.spotify.com/[intl-xx/]track|album|playlist/<id>[?si=...]
_SPOTIFY_URL_RE = re.compile(
    r"https?://open\.spotify\.com/(?:intl-[a-z]{2}/)?"
    r"(track|album|playlist)/(" + _ID + r")"
)

# только треки (основной поддерживаемый тип)
_SPOTIFY_TRACK_RE = re.compile(
    r"https?://open\.spotify\.com/(?:intl-[a-z]{2}/)?"
    r"track/(" + _ID + r")"
)

# альбомы/плейлисты — на MVP не поддерживаем, но отличаем от невалидного текста
_SPOTIFY_COLLECTION_RE = re.compile(
    r"https?://open\.spotify\.com/(?:intl-[a-z]{2}/)?"
    r"(album|playlist)/(" + _ID + r")"
)

# подкасты/эпизоды — для явного отлова и сообщения "не поддерживается"
_SPOTIFY_UNSUPPORTED_RE = re.compile(
    r"https?://open\.spotify\.com/(?:intl-[a-z]{2}/)?"
    r"(episode|show)/(" + _ID + r")"
)


def is_spotify_url(text: str) -> bool:
    """True только для ссылок на одиночный трек Spotify.

    На MVP мы поддерживаем только /track/. Для /album/ и /playlist/
    используй is_spotify_album_or_playlist.
    """
    if not text:
        return False
    return bool(_SPOTIFY_TRACK_RE.search(text))


def is_spotify_album_or_playlist(text: str) -> bool:
    """True, если в тексте ссылка на альбом или плейлист Spotify."""
    if not text:
        return False
    return bool(_SPOTIFY_COLLECTION_RE.search(text))


def is_spotify_unsupported_url(text: str) -> bool:
    """True, если в тексте ссылка на episode/show — их мы не поддерживаем."""
    if not text:
        return False
    return bool(_SPOTIFY_UNSUPPORTED_RE.search(text))


def parse_spotify_url(text: str) -> tuple[SpotifyKind, str] | None:
    """Возвращает (kind, spotify_id) или None, если ссылка невалидна."""
    match = _SPOTIFY_URL_RE.search(text or "")
    if not match:
        return None
    kind = match.group(1)  # type: ignore[assignment]
    return kind, match.group(2)  # type: ignore[return-value]


def clean_spotify_url(text: str) -> str:
    """Возвращает каноничный URL трека/альбома/плейлиста без query и intl-префиксов."""
    parsed = parse_spotify_url(text)
    if not parsed:
        return text
    kind, spotify_id = parsed
    return f"https://open.spotify.com/{kind}/{spotify_id}"


def format_duration(seconds: int) -> str:
    """Форматирует длительность в M:SS или H:MM:SS."""
    if seconds < 0:
        seconds = 0
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
