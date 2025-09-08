import os
import typing as t
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

type AsyncSessionContext = t.AsyncContextManager[AsyncSession]

engine = create_async_engine(
    os.getenv("DATABASE_URL", "sqlite+aiosqlite:///database.sqlite"),
    pool_size=20,
    max_overflow=0,
    echo=False,
)
async_session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> t.AsyncGenerator[AsyncSession, None]:  # pragma: no cover
    try:
        async with async_session_factory() as session:
            yield session
    except Exception as e:
        await session.rollback()
        await session.close()
        raise e
