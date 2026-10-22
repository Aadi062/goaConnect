"""
Pytest configuration: in-memory SQLite for unit tests, shared async client.
Compatible with pytest-asyncio 1.4.x.
"""
import asyncio
import os

# Set test DATABASE_URL before any app imports
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-must-be-32-chars-xyz")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.db.models.user import User
import app.db.models.security  # noqa - register models
import app.db.models.tourism   # noqa - register models
import uuid

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
async def client(db_session):
    # Import app here to avoid early engine creation
    from app.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def test_viewer_user(db_session) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email="viewer@goatest.com",
        username="testviewer",
        hashed_password=hash_password("Test@12345"),
        role="viewer",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def test_analyst_user(db_session) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email="analyst@goatest.com",
        username="testanalyst",
        hashed_password=hash_password("Test@12345"),
        role="analyst",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def test_security_user(db_session) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email="security@goatest.com",
        username="testsecurity",
        hashed_password=hash_password("Test@12345"),
        role="security_analyst",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def security_token(client, test_security_user, db_session) -> str:
    """Login as security analyst and return access token."""
    response = await client.post("/api/v1/auth/login", json={
        "username": "testsecurity",
        "password": "Test@12345",
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture
async def analyst_token(client, test_analyst_user, db_session) -> str:
    response = await client.post("/api/v1/auth/login", json={
        "username": "testanalyst",
        "password": "Test@12345",
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]
