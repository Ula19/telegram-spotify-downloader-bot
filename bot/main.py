"""Точка входа — запуск Spotify-бота"""
import asyncio
import logging
import os
import sys
import time

# uvloop ускоряет asyncio в 2-4 раза (не работает на Windows)
try:
    import uvloop
    uvloop.install()
except ImportError:
    pass

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# флаг-файл для crash recovery
CRASH_FLAG = ".crash_flag"


async def main() -> None:
    """Инициализация и запуск бота."""
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # роутеры (порядок важен: download ловит все текстовые сообщения — последний)
    from bot.handlers import admin, download, start
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(download.router)

    # алерты админу о падении источников (Spotify API / YouTube)
    download.setup_fallback_alerts(bot)

    # мидлвари
    from bot.middlewares.rate_limit import RateLimitMiddleware
    from bot.middlewares.subscription import SubscriptionMiddleware

    dp.message.middleware(RateLimitMiddleware())
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())

    async def _background_cleanup() -> None:
        """Фоновая задача: очистка памяти и /tmp каждые 5 минут."""
        import glob
        from bot.middlewares.rate_limit import cleanup_stale_entries
        while True:
            await asyncio.sleep(300)
            removed = cleanup_stale_entries()
            if removed:
                logger.info("Фоновая очистка: удалено %d записей rate limit", removed)
            # чистим старые файлы /tmp/spotify_bot (старше 30 минут)
            now = time.time()
            cutoff = now - 30 * 60
            cleaned = 0
            for f in glob.glob("/tmp/spotify_bot/**/*", recursive=True):
                try:
                    if os.path.isfile(f) and os.path.getmtime(f) < cutoff:
                        os.remove(f)
                        cleaned += 1
                except OSError:
                    pass
            if cleaned:
                logger.info("Фоновая очистка: удалено %d временных файлов", cleaned)

    @dp.startup()
    async def on_startup() -> None:
        # создаём таблицы в БД
        from bot.database import engine
        from bot.database.models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Таблицы БД созданы")

        # статус прокси (логин/пароль прячем)
        from urllib.parse import urlsplit

        def _safe_proxy(url: str) -> str:
            p = urlsplit(url)
            return f"{p.scheme}://{p.hostname}:{p.port}" if p.hostname else "задан"

        logger.info(
            "Прокси RapidAPI: %s",
            _safe_proxy(settings.proxy_url) if settings.proxy_url else "нет (напрямую)",
        )
        spotdl_proxy = settings.spotdl_proxy_url or settings.proxy_url
        logger.info(
            "Прокси spotdl: %s",
            _safe_proxy(spotdl_proxy) if spotdl_proxy else "нет (напрямую)",
        )

        # crash recovery
        if os.path.exists(CRASH_FLAG):
            logger.warning("Обнаружен crash-flag — предыдущий запуск завершился аварийно")
            os.remove(CRASH_FLAG)
        with open(CRASH_FLAG, "w") as f:
            f.write("running")

        asyncio.create_task(_background_cleanup())
        logger.info("Фоновая очистка запущена (интервал 5 мин)")

        bot_info = await bot.get_me()
        logger.info(f"Бот @{bot_info.username} запущен!")

        # дефолтное меню команд Telegram
        from bot.utils.commands import set_default_commands
        await set_default_commands(bot)
        logger.info("Дефолтное меню команд установлено")

    @dp.shutdown()
    async def on_shutdown() -> None:
        if os.path.exists(CRASH_FLAG):
            os.remove(CRASH_FLAG)
        logger.info("Бот остановлен")

    try:
        logger.info("Запуск polling...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
