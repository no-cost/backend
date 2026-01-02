from contextlib import asynccontextmanager

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, create_async_engine

from database.models import Base
from database.session import get_session
from main import API

test_engine = create_async_engine("sqlite+aiosqlite:///test_database.sqlite")
test_async_session_factory = async_sessionmaker[AsyncSession](test_engine)


@asynccontextmanager
async def get_test_session():
    async with test_async_session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()  # otherwise the test loop hangs forever


@pytest_asyncio.fixture(scope="function")
async def test_db_session(setup_test_db):
    async with get_test_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_db_session):
    API.dependency_overrides[get_session] = lambda: get_test_session()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=API), base_url="http://no-cost.local"
        ) as ac:
            yield ac
    finally:
        API.dependency_overrides.pop(get_session)
