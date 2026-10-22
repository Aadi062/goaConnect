"""Security tests: alert creation, approval workflow, audit trail, RBAC."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_alert_requires_security_role(client: AsyncClient, analyst_token: str):
    """Analyst role cannot create security alerts — only security_analyst/admin."""
    r = await client.post(
        "/api/v1/security/alerts",
        json={
            "title": "Test Alert",
            "description": "Brute force detected",
            "severity": "high",
            "alert_type": "brute_force",
            "source_agent": "auth_guardian",
            "confidence": 0.85,
        },
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_create_alert_success(client: AsyncClient, security_token: str):
    r = await client.post(
        "/api/v1/security/alerts",
        json={
            "title": "Brute Force Detected",
            "description": "5 failed logins from 192.168.1.100",
            "severity": "high",
            "alert_type": "brute_force_suspected",
            "source_agent": "authentication_guardian",
            "affected_resource": "user:testuser1",
            "confidence": 0.85,
        },
        headers={"Authorization": f"Bearer {security_token}"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "open"
    assert data["severity"] == "high"
    assert data["is_verified"] is False
    return data["id"]


@pytest.mark.asyncio
async def test_get_alert_by_id(client: AsyncClient, security_token: str):
    # Create first
    create = await client.post(
        "/api/v1/security/alerts",
        json={
            "title": "Get Test Alert",
            "description": "desc",
            "severity": "low",
            "alert_type": "test",
            "source_agent": "test_agent",
        },
        headers={"Authorization": f"Bearer {security_token}"},
    )
    alert_id = create.json()["id"]

    r = await client.get(f"/api/v1/security/alerts/{alert_id}", headers={"Authorization": f"Bearer {security_token}"})
    assert r.status_code == 200
    assert r.json()["id"] == alert_id


@pytest.mark.asyncio
async def test_patch_alert_status(client: AsyncClient, security_token: str):
    create = await client.post(
        "/api/v1/security/alerts",
        json={
            "title": "Patch Test",
            "description": "desc",
            "severity": "medium",
            "alert_type": "test",
            "source_agent": "test_agent",
        },
        headers={"Authorization": f"Bearer {security_token}"},
    )
    alert_id = create.json()["id"]

    r = await client.patch(
        f"/api/v1/security/alerts/{alert_id}",
        json={"status": "investigating", "assigned_to": "analyst1"},
        headers={"Authorization": f"Bearer {security_token}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "investigating"


@pytest.mark.asyncio
async def test_security_posture_endpoint(client: AsyncClient, security_token: str):
    r = await client.get("/api/v1/security/posture", headers={"Authorization": f"Bearer {security_token}"})
    assert r.status_code == 200
    data = r.json()
    assert "open_alerts" in data
    assert "posture" in data


@pytest.mark.asyncio
async def test_approval_workflow(client: AsyncClient, security_token: str):
    # Create approval request
    r = await client.post(
        "/api/v1/security/approvals",
        json={
            "requesting_agent": "containment_advisor",
            "action_type": "temporary_account_lockout",
            "action_description": "Lock account user123 for 15 minutes",
            "risk_level": "medium",
            "expires_in_minutes": 60,
        },
        headers={"Authorization": f"Bearer {security_token}"},
    )
    assert r.status_code == 201
    approval_id = r.json()["id"]

    # Approve it
    decide = await client.post(
        f"/api/v1/security/approvals/{approval_id}/decide",
        json={"approved": True, "note": "Confirmed — lockout approved by SOC analyst"},
        headers={"Authorization": f"Bearer {security_token}"},
    )
    assert decide.status_code == 200
    assert decide.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_double_approval_rejected(client: AsyncClient, security_token: str):
    r = await client.post(
        "/api/v1/security/approvals",
        json={
            "requesting_agent": "test_agent",
            "action_type": "test_action",
            "action_description": "Test double approval",
            "risk_level": "low",
            "expires_in_minutes": 60,
        },
        headers={"Authorization": f"Bearer {security_token}"},
    )
    approval_id = r.json()["id"]

    await client.post(
        f"/api/v1/security/approvals/{approval_id}/decide",
        json={"approved": True},
        headers={"Authorization": f"Bearer {security_token}"},
    )
    # Second decision on already-actioned approval
    r2 = await client.post(
        f"/api/v1/security/approvals/{approval_id}/decide",
        json={"approved": False},
        headers={"Authorization": f"Bearer {security_token}"},
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_audit_log_populated(client: AsyncClient, security_token: str):
    """Creating an alert should produce an audit log entry."""
    await client.post(
        "/api/v1/security/alerts",
        json={
            "title": "Audit Test Alert",
            "description": "For audit trail test",
            "severity": "low",
            "alert_type": "test",
            "source_agent": "test_agent",
        },
        headers={"Authorization": f"Bearer {security_token}"},
    )
    r = await client.get("/api/v1/security/audit", headers={"Authorization": f"Bearer {security_token}"})
    assert r.status_code == 200
    events = r.json()
    assert len(events) >= 1
