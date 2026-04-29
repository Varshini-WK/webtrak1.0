from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.settings import get_settings


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self) -> None:
        settings = get_settings()
        self.engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            future=True,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @asynccontextmanager
    async def tx(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as session:
            async with session.begin():
                yield session

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as session:
            yield session

    async def connect(self) -> None:
        # Engine is lazy; keep this for startup compatibility.
        return None

    async def disconnect(self) -> None:
        await self.engine.dispose()


db = Database()


async def get_db() -> Database:
    return db
