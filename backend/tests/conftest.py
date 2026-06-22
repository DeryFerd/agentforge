"""Pytest configuration and shared fixtures for AgentForge backend tests.

Uses testcontainers-python with real PostgreSQL for accurate testing.
Falls back to SQLite+aiosqlite for environments without Docker.
"""

import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import app


# Module-level reference to the testcontainer for cleanup
_pg_container = None


def _get_test_database_url() -> str:
    """Get test database URL — prefer testcontainers PostgreSQL, fall back to SQLite."""
    global _pg_container
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        return url

    # Try testcontainers
    try:
        from testcontainers.postgres import PostgresContainer

        _pg_container = PostgresContainer("postgres:16-alpine")
        _pg_container.start()
        url = _pg_container.get_connection_url().replace("postgresql://", "postgresql+asyncpg://")
        # Store for reuse across test modules
        os.environ["TEST_DATABASE_URL"] = url
        return url
    except Exception:
        # Fallback to SQLite for environments without Docker
        return "sqlite+aiosqlite:///./test.db"


TEST_DATABASE_URL = _get_test_database_url()

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def cleanup_testcontainer():
    """Ensure the PostgreSQL testcontainer is stopped after all tests complete."""
    yield
    global _pg_container
    if _pg_container is not None:
        try:
            _pg_container.stop()
        except Exception:
            pass  # Best effort cleanup


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test and drop them after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override the DB dependency for tests."""
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Apply the override
app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Direct database session for test setup."""
    async with TestSessionLocal() as session:
        yield session
