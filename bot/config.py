"""Конфигурация бота — все настройки из .env"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # токен бота
    bot_token: str

    # PostgreSQL
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "bot_4_spotify"
    db_user: str = "postgres"
    db_password: str = ""

    # юзернейм бота (для рекламной подписи)
    bot_username: str = ""

    # админы бота (через запятую в .env)
    admin_ids: str = ""
    admin_username: str = "admin"

    # RapidAPI ключ для провайдера spotify-downloader9
    # (получить: rapidapi.com → Spotify Downloader → подписаться → скопировать X-RapidAPI-Key)
    rapidapi_key: str = ""

    # прокси (опционально, если RapidAPI заблокирован в стране хостинга)
    proxy_url: str = ""

    # отдельный прокси только для spotdl (WARP) — чтобы YouTube-трафик шёл через него,
    # а RapidAPI оставался прямым. Если пусто — spotdl берёт proxy_url.
    spotdl_proxy_url: str = ""

    # ключи Spotify API (опционально) — нужны только spotdl-фоллбеку для точного мэтчинга
    # без них spotdl тоже работает, но на урезанном SpotipyFree
    spotify_client_id: str = ""
    spotify_client_secret: str = ""

    # путь к cookie-файлу YouTube (опционально) — обход "Sign in to confirm you're not a bot"
    # в spotdl, когда качаем с помеченного IP/прокси. Формат Netscape (экспорт из браузера).
    spotdl_cookie_file: str = ""

    # кэш скачиваний (дни)
    cache_ttl_days: int = 1

    @property
    def admin_id_list(self) -> list[int]:
        """Парсит admin_ids из строки в список int"""
        if not self.admin_ids:
            return []
        return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip()]

    @property
    def db_url(self) -> str:
        """URL для подключения к PostgreSQL через asyncpg"""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# глобальный экземпляр настроек
settings = Settings()
