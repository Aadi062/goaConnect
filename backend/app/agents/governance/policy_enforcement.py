"""
Policy Enforcement Service — deterministic, LLM-independent authorization.
This is the final enforcement gate. Agent permissions are checked here, not in prompts.
"""
from __future__ import annotations

from app.agents.core.base import AgentRole, ToolPermission
from app.core.logging import get_logger

logger = get_logger("policy_enforcement")

# Explicit permission matrix — change requires code review, not prompt editing
AGENT_PERMISSIONS: dict[AgentRole, frozenset[ToolPermission]] = {
    AgentRole.SECURITY_COMMANDER: frozenset({
        ToolPermission.READ_AUDIT_LOG,
        ToolPermission.READ_ALERTS,
        ToolPermission.REQUEST_APPROVAL,
    }),
    AgentRole.SOC_ORCHESTRATOR: frozenset({
        ToolPermission.READ_ALERTS,
        ToolPermission.WRITE_ALERTS,
        ToolPermission.READ_AUDIT_LOG,
        ToolPermission.REQUEST_APPROVAL,
    }),
    AgentRole.AUTHENTICATION_GUARDIAN: frozenset({
        ToolPermission.READ_AUDIT_LOG,
        ToolPermission.WRITE_ALERTS,
    }),
    AgentRole.API_SECURITY_GUARDIAN: frozenset({
        ToolPermission.READ_AUDIT_LOG,
        ToolPermission.WRITE_ALERTS,
    }),
    AgentRole.DATABASE_GUARDIAN: frozenset({
        ToolPermission.READ_AUDIT_LOG,
        ToolPermission.WRITE_ALERTS,
    }),
    AgentRole.ALERT_TRIAGE: frozenset({
        ToolPermission.READ_ALERTS,
        ToolPermission.WRITE_ALERTS,
    }),
    AgentRole.RISK_PRIORITIZATION: frozenset({
        ToolPermission.READ_ALERTS,
        ToolPermission.READ_AUDIT_LOG,
    }),
    AgentRole.CONTAINMENT_ADVISOR: frozenset({
        ToolPermission.READ_ALERTS,
        ToolPermission.READ_AUDIT_LOG,
        ToolPermission.REQUEST_APPROVAL,
    }),
    AgentRole.EVIDENCE_VERIFICATION: frozenset({
        ToolPermission.READ_AUDIT_LOG,
        ToolPermission.READ_ALERTS,
        ToolPermission.READ_LOGS,
    }),
    AgentRole.SECURE_CODE_REVIEW: frozenset({
        ToolPermission.RUN_SAST,
        ToolPermission.READ_CONFIG,
    }),
    AgentRole.DEPENDENCY_AUDIT: frozenset({
        ToolPermission.READ_CONFIG,
    }),
    AgentRole.CONFIGURATION_AUDIT: frozenset({
        ToolPermission.READ_CONFIG,
    }),
    AgentRole.THREAT_INTELLIGENCE: frozenset({
        ToolPermission.READ_THREAT_INTEL,
        ToolPermission.READ_ALERTS,
    }),
    AgentRole.TRAVEL_ASSISTANT: frozenset({
        ToolPermission.READ_PLACES,
    }),
    AgentRole.ITINERARY_PLANNER: frozenset({
        ToolPermission.READ_PLACES,
    }),
    AgentRole.HERITAGE_GUIDE: frozenset({
        ToolPermission.READ_PLACES,
    }),
    AgentRole.HUMAN_APPROVAL_COORDINATOR: frozenset({
        ToolPermission.REQUEST_APPROVAL,
        ToolPermission.READ_ALERTS,
    }),
    AgentRole.MODEL_SAFETY_GUARDIAN: frozenset({
        ToolPermission.READ_AUDIT_LOG,
    }),
}

# Actions requiring mandatory human approval (never auto-executed)
HIGH_IMPACT_ACTIONS = frozenset({
    "account_suspension",
    "api_key_revocation",
    "production_config_change",
    "sensitive_data_export",
    "database_schema_change",
    "firewall_rule_change",
    "bulk_user_delete",
    "incident_escalation_to_external",
})


def enforce_agent_permission(agent_role: AgentRole, requested_tool: ToolPermission) -> bool:
    """
    Returns True if the agent is permitted to use the tool.
    Logs a violation if denied. This is the backend enforcement — prompts cannot override this.
    """
    allowed = AGENT_PERMISSIONS.get(agent_role, frozenset())
    permitted = requested_tool in allowed

    if not permitted:
        logger.warning(
            "policy_violation",
            agent_role=agent_role.value,
            requested_tool=requested_tool.value,
            action="blocked",
        )

    return permitted


def is_high_impact_action(action: str) -> bool:
    return action in HIGH_IMPACT_ACTIONS


def validate_agent_tool_call(agent_role: AgentRole, tool: ToolPermission, action: str) -> dict:
    """
    Full validation for an agent tool call.
    Returns a decision dict with 'allowed', 'requires_approval', and 'reason'.
    """
    permitted = enforce_agent_permission(agent_role, tool)
    requires_approval = is_high_impact_action(action)

    if not permitted:
        return {
            "allowed": False,
            "requires_approval": False,
            "reason": f"Agent {agent_role.value} does not have permission to use {tool.value}",
        }

    if requires_approval:
        return {
            "allowed": True,
            "requires_approval": True,
            "reason": f"Action '{action}' is high-impact and requires human approval",
        }

    return {"allowed": True, "requires_approval": False, "reason": "Permitted"}
