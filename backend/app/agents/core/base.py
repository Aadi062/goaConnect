"""
Agent base class and typed contracts.
Every agent has: a name, permitted tools, input/output schema, and produces audit evidence.
No agent has unrestricted shell, DB-admin, or OS access.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    SECURITY_COMMANDER = "security_commander"
    SOC_ORCHESTRATOR = "soc_orchestrator"
    THREAT_INTELLIGENCE = "threat_intelligence"
    AUTHENTICATION_GUARDIAN = "authentication_guardian"
    API_SECURITY_GUARDIAN = "api_security_guardian"
    DATABASE_GUARDIAN = "database_guardian"
    ALERT_TRIAGE = "alert_triage"
    INCIDENT_TIMELINE = "incident_timeline"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    CONTAINMENT_ADVISOR = "containment_advisor"
    RISK_PRIORITIZATION = "risk_prioritization"
    EVIDENCE_VERIFICATION = "evidence_verification"
    HUMAN_APPROVAL_COORDINATOR = "human_approval_coordinator"
    POLICY_ENFORCEMENT = "policy_enforcement"
    MODEL_SAFETY_GUARDIAN = "model_safety_guardian"
    SECURE_CODE_REVIEW = "secure_code_review"
    DEPENDENCY_AUDIT = "dependency_audit"
    CONFIGURATION_AUDIT = "configuration_audit"
    REMEDIATION_ADVISOR = "remediation_advisor"
    TRAVEL_ASSISTANT = "travel_assistant"
    ITINERARY_PLANNER = "itinerary_planner"
    HERITAGE_GUIDE = "heritage_guide"


class ToolPermission(str, Enum):
    READ_AUDIT_LOG = "read:audit_log"
    READ_ALERTS = "read:alerts"
    WRITE_ALERTS = "write:alerts"
    READ_USERS = "read:users"
    READ_PLACES = "read:places"
    WRITE_PLACES = "write:places"
    READ_LOGS = "read:logs"
    RUN_SAST = "run:sast"
    RUN_DAST_AUTHORIZED = "run:dast_authorized"
    READ_CONFIG = "read:config"
    REQUEST_APPROVAL = "request:approval"
    SEND_NOTIFICATION = "send:notification"
    READ_THREAT_INTEL = "read:threat_intel"


class AgentInput(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str
    payload: dict[str, Any]
    requester_id: Optional[str] = None
    priority: int = Field(default=5, ge=1, le=10)
    deadline_seconds: int = Field(default=30, ge=1, le=300)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentOutput(BaseModel):
    task_id: str
    agent_id: str
    agent_role: str
    status: str  # success / partial / failed / blocked
    result: Optional[dict[str, Any]] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    reasoning: Optional[str] = None
    requires_human_approval: bool = False
    audit_trail: list[str] = Field(default_factory=list)
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"extra": "forbid"}


class BaseAgent(ABC):
    """
    Abstract base for all GoaConnect agents.
    Subclasses declare their permitted_tools set.
    All tool calls are validated against this set before execution.
    """

    role: AgentRole
    permitted_tools: set[ToolPermission] = set()
    max_retries: int = 2
    timeout_seconds: int = 30

    def __init__(self):
        self.agent_id = f"{self.role.value}:{str(uuid.uuid4())[:8]}"

    def _check_permission(self, tool: ToolPermission) -> None:
        if tool not in self.permitted_tools:
            raise PermissionError(
                f"Agent '{self.agent_id}' attempted to use '{tool.value}' "
                f"which is not in its permitted_tools set."
            )

    @abstractmethod
    async def run(self, task: AgentInput) -> AgentOutput:
        """Execute the agent task. Must return AgentOutput."""
        ...

    def _build_output(
        self,
        task_id: str,
        status: str,
        result: Optional[dict] = None,
        confidence: float = 0.0,
        evidence: Optional[list] = None,
        reasoning: Optional[str] = None,
        requires_human_approval: bool = False,
        audit_trail: Optional[list[str]] = None,
    ) -> AgentOutput:
        return AgentOutput(
            task_id=task_id,
            agent_id=self.agent_id,
            agent_role=self.role.value,
            status=status,
            result=result,
            confidence=confidence,
            evidence=evidence or [],
            reasoning=reasoning,
            requires_human_approval=requires_human_approval,
            audit_trail=audit_trail or [f"Agent {self.agent_id} executed task {task_id}"],
        )
