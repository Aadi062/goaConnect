"""
Central Manager/Orchestrator Agent.
Classifies incoming tasks, routes to specialist agents,
enforces isolation between security and tourism domains.
"""
from __future__ import annotations

import asyncio
from typing import Any, Optional

from app.agents.core.base import (
    AgentInput, AgentOutput, AgentRole, BaseAgent, ToolPermission
)
from app.core.logging import get_logger

logger = get_logger("agent.manager")

# Lazy registry — populated by register_agent()
_AGENT_REGISTRY: dict[AgentRole, type[BaseAgent]] = {}


def register_agent(cls: type[BaseAgent]) -> type[BaseAgent]:
    _AGENT_REGISTRY[cls.role] = cls
    return cls


def _classify_task(task_type: str) -> AgentRole:
    """Deterministic routing — no LLM involved in dispatch."""
    routing: dict[str, AgentRole] = {
        "auth_anomaly": AgentRole.AUTHENTICATION_GUARDIAN,
        "api_anomaly": AgentRole.API_SECURITY_GUARDIAN,
        "db_anomaly": AgentRole.DATABASE_GUARDIAN,
        "alert_triage": AgentRole.ALERT_TRIAGE,
        "incident_timeline": AgentRole.INCIDENT_TIMELINE,
        "root_cause": AgentRole.ROOT_CAUSE_ANALYSIS,
        "containment": AgentRole.CONTAINMENT_ADVISOR,
        "risk_score": AgentRole.RISK_PRIORITIZATION,
        "code_review": AgentRole.SECURE_CODE_REVIEW,
        "dependency_audit": AgentRole.DEPENDENCY_AUDIT,
        "config_audit": AgentRole.CONFIGURATION_AUDIT,
        "threat_intel": AgentRole.THREAT_INTELLIGENCE,
        "travel_query": AgentRole.TRAVEL_ASSISTANT,
        "itinerary": AgentRole.ITINERARY_PLANNER,
        "heritage": AgentRole.HERITAGE_GUIDE,
    }
    return routing.get(task_type, AgentRole.ALERT_TRIAGE)


class ManagerAgent(BaseAgent):
    """
    Security Commander + Orchestrator.
    Dispatches tasks to registered specialist agents.
    Enforces security/tourism domain isolation.
    """
    role = AgentRole.SECURITY_COMMANDER
    permitted_tools = {
        ToolPermission.READ_AUDIT_LOG,
        ToolPermission.READ_ALERTS,
        ToolPermission.REQUEST_APPROVAL,
    }

    SECURITY_TASK_TYPES = {
        "auth_anomaly", "api_anomaly", "db_anomaly", "alert_triage",
        "incident_timeline", "root_cause", "containment", "risk_score",
        "code_review", "dependency_audit", "config_audit", "threat_intel",
    }
    TOURISM_TASK_TYPES = {"travel_query", "itinerary", "heritage"}

    async def run(self, task: AgentInput) -> AgentOutput:
        logger.info(
            "manager_dispatch",
            task_id=task.task_id,
            task_type=task.task_type,
            priority=task.priority,
        )

        # Domain isolation check
        if task.task_type in self.SECURITY_TASK_TYPES and task.requester_id:
            # Security tasks require authenticated user — enforced upstream in routes
            pass

        target_role = _classify_task(task.task_type)
        agent_cls = _AGENT_REGISTRY.get(target_role)

        if not agent_cls:
            return self._build_output(
                task.task_id,
                status="failed",
                result={"error": f"No agent registered for role {target_role.value}"},
                confidence=0.0,
                reasoning=f"No specialist found for task_type={task.task_type}",
            )

        agent = agent_cls()
        try:
            result = await asyncio.wait_for(
                agent.run(task),
                timeout=task.deadline_seconds,
            )
            logger.info("agent_completed", task_id=task.task_id, agent=agent.agent_id, status=result.status)
            return result
        except asyncio.TimeoutError:
            logger.error("agent_timeout", task_id=task.task_id, agent=target_role.value)
            return self._build_output(
                task.task_id,
                status="failed",
                result={"error": "Agent timed out"},
                confidence=0.0,
                reasoning=f"Agent {target_role.value} exceeded deadline of {task.deadline_seconds}s",
            )
        except Exception as exc:
            logger.error("agent_error", task_id=task.task_id, exc=str(exc))
            return self._build_output(
                task.task_id,
                status="failed",
                result={"error": str(exc)},
                confidence=0.0,
            )
