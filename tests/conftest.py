import typing as t
from contextlib import asynccontextmanager

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.models import Base
from database.session import get_session
from main import FF_API

test_engine = create_async_engine("sqlite+aiosqlite:///test_database.sqlite")
test_async_session_factory = async_sessionmaker(test_engine)


@asynccontextmanager
async def get_test_session() -> t.AsyncGenerator[AsyncSession, None]:
    try:
        async with test_async_session_factory() as session:
            yield session
    except (
        Exception
    ) as e:  # pragma: no cover # TODO: why is this never caught in coverage?
        await session.rollback()
        await session.close()
        raise e


@pytest_asyncio.fixture(scope="session")
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def test_db_session(setup_test_db):
    async with get_test_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_db_session):
    FF_API.dependency_overrides[get_session] = lambda: get_test_session()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=FF_API), base_url="http://freeflarum.test"
        ) as ac:
            yield ac
    finally:
        FF_API.dependency_overrides.pop(get_session)
