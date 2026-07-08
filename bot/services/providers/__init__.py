"""Пакет провайдеров скачивания треков.

Каждый провайдер реализует BaseProvider (get_track + download_track).
Оркестратор SpotifyDownloader (bot/services/spotify.py) держит их список
и перебирает по цепочке, пока кто-то не отдаст трек.
"""
