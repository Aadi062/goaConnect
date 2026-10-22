"""Unit tests for authentication: register, login, JWT, lockout, role enforcement."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    r = await client.post("/api/v1/auth/register", json={
        "email": "newuser@goatest.com",
        "username": "newuser1",
        "password": "Secure@Pass1",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["username"] == "newuser1"
    assert data["role"] == "viewer"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "dup@goatest.com", "username": "dupuser1", "password": "Secure@Pass1"}
    r1 = await client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201
    payload["username"] = "dupuser2"
    r2 = await client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    r = await client.post("/api/v1/auth/register", json={
        "email": "weak@goatest.com",
        "username": "weakuser",
        "password": "password",  # no uppercase, no digit, no special char
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_viewer_user):
    r = await client.post("/api/v1/auth/login", json={
        "username": "testviewer",
        "password": "Test@12345",
    })
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_viewer_user):
    r = await client.post("/api/v1/auth/login", json={
        "username": "testviewer",
        "password": "WrongPassword1!",
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_whoami_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_whoami_with_token(client: AsyncClient, test_viewer_user):
    login = await client.post("/api/v1/auth/login", json={
        "username": "testviewer",
        "password": "Test@12345",
    })
    token = login.json()["access_token"]
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "testviewer"


@pytest.mark.asyncio
async def test_invalid_token_rejected(client: AsyncClient):
    r = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalidtoken.bad.jwt"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_viewer_cannot_access_security_alerts(client: AsyncClient, test_viewer_user):
    """Role enforcement: viewer cannot list security alerts (requires analyst/security role)."""
    login = await client.post("/api/v1/auth/login", json={
        "username": "testviewer",
        "password": "Test@12345",
    })
    token = login.json()["access_token"]
    r = await client.get("/api/v1/security/alerts", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_security_analyst_can_access_alerts(client: AsyncClient, security_token: str):
    r = await client.get("/api/v1/security/alerts", headers={"Authorization": f"Bearer {security_token}"})
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data
