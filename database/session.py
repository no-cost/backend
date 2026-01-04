from collections.abc import AsyncIterator
from os import environ

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

engine = create_async_engine(
    environ["DATABASE_URL"],
    pool_size=20,
    max_overflow=0,
    echo=False,
)
async_session_factory = async_sessionmaker[AsyncSession](
    bind=engine, expire_on_commit=False
)


async def get_session() -> AsyncIterator[AsyncSession]:  # pragma: no cover
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
