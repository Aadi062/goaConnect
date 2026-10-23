"""Tests for agent orchestration: routing, permission enforcement, policy gate."""
import pytest
from app.agents.core.base import AgentInput, AgentRole, ToolPermission
from app.agents.core.manager import ManagerAgent
from app.agents.governance.policy_enforcement import (
    enforce_agent_permission, validate_agent_tool_call, is_high_impact_action
)
import app.agents.security.detection_agents  # noqa — register agents
import app.agents.tourism.tourism_agents  # noqa


@pytest.mark.asyncio
async def test_manager_routes_auth_anomaly():
    task = AgentInput(task_type="auth_anomaly", payload={"login_events": [], "user_id": "u1"})
    manager = ManagerAgent()
    result = await manager.run(task)
    assert result.status == "success"
    assert result.agent_role == AgentRole.AUTHENTICATION_GUARDIAN.value


@pytest.mark.asyncio
async def test_manager_routes_travel_query():
    task = AgentInput(task_type="travel_query", payload={"query": "beaches", "days": 2})
    manager = ManagerAgent()
    result = await manager.run(task)
    assert result.status == "success"
    assert result.agent_role == AgentRole.TRAVEL_ASSISTANT.value


@pytest.mark.asyncio
async def test_authentication_guardian_detects_brute_force():
    from app.agents.security.detection_agents import AuthenticationGuardianAgent
    agent = AuthenticationGuardianAgent()
    events = [{"outcome": "failure", "ip": "1.2.3.4"}] * 7
    task = AgentInput(task_type="auth_anomaly", payload={"login_events": events, "user_id": "u99"})
    result = await agent.run(task)
    assert result.status == "success"
    findings = result.result["findings"]
    assert any(f["type"] == "brute_force_suspected" for f in findings)
    assert result.confidence > 0.5


@pytest.mark.asyncio
async def test_authentication_guardian_clean_login():
    from app.agents.security.detection_agents import AuthenticationGuardianAgent
    agent = AuthenticationGuardianAgent()
    events = [{"outcome": "success", "ip": "1.2.3.4"}]
    task = AgentInput(task_type="auth_anomaly", payload={"login_events": events, "user_id": "u98"})
    result = await agent.run(task)
    assert result.result["findings"] == []


@pytest.mark.asyncio
async def test_alert_triage_deduplication():
    from app.agents.security.detection_agents import AlertTriageAgent
    agent = AlertTriageAgent()
    alerts = [
        {"alert_type": "brute_force", "affected_resource": "user1", "severity": "high"},
        {"alert_type": "brute_force", "affected_resource": "user1", "severity": "high"},
        {"alert_type": "brute_force", "affected_resource": "user1", "severity": "medium"},
        {"alert_type": "api_abuse", "affected_resource": "endpoint/login", "severity": "medium"},
    ]
    task = AgentInput(task_type="alert_triage", payload={"alerts": alerts})
    result = await agent.run(task)
    assert result.result["original_count"] == 4
    assert result.result["deduplicated_count"] == 2


@pytest.mark.asyncio
async def test_containment_advisor_requires_approval_for_high_risk():
    from app.agents.security.detection_agents import ContainmentAdvisorAgent
    agent = ContainmentAdvisorAgent()
    task = AgentInput(task_type="containment", payload={"alert_type": "authorization_abuse"})
    result = await agent.run(task)
    assert result.requires_human_approval is True


@pytest.mark.asyncio
async def test_containment_advisor_no_approval_for_low_risk():
    from app.agents.security.detection_agents import ContainmentAdvisorAgent
    agent = ContainmentAdvisorAgent()
    task = AgentInput(task_type="containment", payload={"alert_type": "rate_limit_exhaustion"})
    result = await agent.run(task)
    assert result.requires_human_approval is False


@pytest.mark.asyncio
async def test_travel_assistant_returns_recommendations():
    from app.agents.tourism.tourism_agents import TravelAssistantAgent
    agent = TravelAssistantAgent()
    task = AgentInput(task_type="travel_query", payload={"query": "beach", "days": 3, "budget_inr": 5000})
    result = await agent.run(task)
    assert result.status == "success"
    assert len(result.result["response"]) > 0
    assert len(result.result["source_citations"]) > 0
    assert "agent_model" in result.result


@pytest.mark.asyncio
async def test_itinerary_planner_generates_days():
    from app.agents.tourism.tourism_agents import ItineraryPlannerAgent
    agent = ItineraryPlannerAgent()
    task = AgentInput(task_type="itinerary", payload={"days": 3, "budget_inr": 15000, "group_size": 2})
    result = await agent.run(task)
    assert result.status == "success"
    assert len(result.result["itinerary"]) == 3


@pytest.mark.asyncio
async def test_heritage_guide_known_site():
    from app.agents.tourism.tourism_agents import HeritageGuideAgent
    agent = HeritageGuideAgent()
    task = AgentInput(task_type="heritage", payload={"site": "basilica of bom jesus"})
    result = await agent.run(task)
    assert result.status == "success"
    assert "UNESCO" in result.result["type"]


@pytest.mark.asyncio
async def test_heritage_guide_unknown_site():
    from app.agents.tourism.tourism_agents import HeritageGuideAgent
    agent = HeritageGuideAgent()
    task = AgentInput(task_type="heritage", payload={"site": "nonexistent place xyz"})
    result = await agent.run(task)
    assert result.status == "partial"


# ──── Policy Enforcement Tests ────

def test_policy_permits_auth_guardian_read_audit():
    result = enforce_agent_permission(AgentRole.AUTHENTICATION_GUARDIAN, ToolPermission.READ_AUDIT_LOG)
    assert result is True


def test_policy_blocks_travel_agent_writing_alerts():
    """Tourism agent must NOT be able to write security alerts."""
    result = enforce_agent_permission(AgentRole.TRAVEL_ASSISTANT, ToolPermission.WRITE_ALERTS)
    assert result is False


def test_policy_blocks_travel_agent_reading_audit():
    result = enforce_agent_permission(AgentRole.TRAVEL_ASSISTANT, ToolPermission.READ_AUDIT_LOG)
    assert result is False


def test_high_impact_action_flagged():
    assert is_high_impact_action("account_suspension") is True
    assert is_high_impact_action("account_suspension") is True
    assert is_high_impact_action("read_alerts") is False


def test_validate_agent_tool_call_permitted():
    decision = validate_agent_tool_call(
        AgentRole.AUTHENTICATION_GUARDIAN,
        ToolPermission.WRITE_ALERTS,
        "create_alert",
    )
    assert decision["allowed"] is True
    assert decision["requires_approval"] is False


def test_validate_agent_tool_call_denied():
    decision = validate_agent_tool_call(
        AgentRole.TRAVEL_ASSISTANT,
        ToolPermission.WRITE_ALERTS,
        "create_alert",
    )
    assert decision["allowed"] is False


def test_validate_high_impact_requires_approval():
    decision = validate_agent_tool_call(
        AgentRole.SOC_ORCHESTRATOR,
        ToolPermission.REQUEST_APPROVAL,
        "account_suspension",
    )
    assert decision["allowed"] is True
    assert decision["requires_approval"] is True


@pytest.mark.asyncio
async def test_agent_timeout():
    """Agent that exceeds deadline returns failed status."""
    import asyncio
    from app.agents.core.base import BaseAgent
    from app.agents.core.manager import _AGENT_REGISTRY

    original = _AGENT_REGISTRY.get(AgentRole.DATABASE_GUARDIAN)

    class SlowAgent(BaseAgent):
        role = AgentRole.DATABASE_GUARDIAN
        permitted_tools = set()
        async def run(self, task):
            await asyncio.sleep(999)
            return self._build_output(task.task_id, "success")

    _AGENT_REGISTRY[AgentRole.DATABASE_GUARDIAN] = SlowAgent
    try:
        task = AgentInput(task_type="db_anomaly", payload={}, deadline_seconds=1)
        manager = ManagerAgent()
        result = await manager.run(task)
        assert result.status == "failed"
        assert "timed out" in result.result["error"].lower()
    finally:
        if original is not None:
            _AGENT_REGISTRY[AgentRole.DATABASE_GUARDIAN] = original
        else:
            _AGENT_REGISTRY.pop(AgentRole.DATABASE_GUARDIAN, None)
