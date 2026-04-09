"""Подключение к PostgreSQL — engine и session"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from bot.config import settings

# движок для работы с БД
engine = create_async_engine(settings.db_url, echo=False)

# фабрика сессий для запросов к БД
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
