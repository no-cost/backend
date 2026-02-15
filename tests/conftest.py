import os

os.environ.setdefault("ALLOWED_DOMAINS", "test.local,test2.local")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test_database.sqlite")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("PHP_VERSION", "8.3")
os.environ.setdefault("TENANTS_ROOT", "/tmp/test_tenants")
os.environ.setdefault("SKELETON_ROOT", "/tmp/test_skeleton")
os.environ.setdefault("BACKUP_HOST_ROOT", "/tmp/test_backups")
os.environ.setdefault("BACKUP_ATTIC_ROOT", "/tmp/test_backup_attic")
os.environ.setdefault("BACKUP_SYSTEM_ROOT", "/tmp/test_backup_system")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("TURNSTILE_KEY", "test-turnstile-key")
os.environ.setdefault("MAILTO", "test@test.local")
os.environ.setdefault("KOFI_VERIFICATION_TOKEN", "test-kofi-token")
os.environ.setdefault("HEALTH_CHECK_TOKEN", "test-health-token")
os.environ.setdefault("INTEGRATION_TEST_TOKEN", "test-integration-token")

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.models import Base

test_engine = create_async_engine("sqlite+aiosqlite:///test_database.sqlite")
test_async_session_factory = async_sessionmaker[AsyncSession](test_engine)


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
    async with test_async_session_factory() as session:
        yield session
