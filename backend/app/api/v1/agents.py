"""Agent orchestration API: submit tasks, check status, policy validation."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Any

from app.core.deps import get_current_user, require_analyst
from app.db.models.user import User
from app.agents.core.base import AgentInput, AgentOutput
from app.agents.core.manager import ManagerAgent
from app.agents.governance.policy_enforcement import validate_agent_tool_call, AgentRole, ToolPermission

# Ensure agents are registered
import app.agents.security.detection_agents  # noqa
import app.agents.tourism.tourism_agents  # noqa

router = APIRouter(prefix="/agents", tags=["agents"])


class TaskRequest(BaseModel):
    task_type: str = Field(max_length=100)
    payload: dict[str, Any]
    priority: int = Field(default=5, ge=1, le=10)
    deadline_seconds: int = Field(default=30, ge=5, le=120)


class PolicyCheckRequest(BaseModel):
    agent_role: str
    tool: str
    action: str


@router.post("/tasks", response_model=AgentOutput)
async def submit_task(
    request: TaskRequest,
    current_user: User = Depends(require_analyst),
):
    """Submit a task to the Manager Agent for routing and execution."""
    task = AgentInput(
        task_type=request.task_type,
        payload=request.payload,
        requester_id=current_user.id,
        priority=request.priority,
        deadline_seconds=request.deadline_seconds,
    )
    manager = ManagerAgent()
    result = await manager.run(task)
    return result


@router.post("/policy/check")
async def check_policy(
    req: PolicyCheckRequest,
    current_user: User = Depends(require_analyst),
):
    """Validate whether an agent role is permitted to use a tool for a given action."""
    try:
        role = AgentRole(req.agent_role)
        tool = ToolPermission(req.tool)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid role or tool: {e}")

    decision = validate_agent_tool_call(role, tool, req.action)
    return decision


@router.get("/roles")
async def list_agent_roles(current_user: User = Depends(require_analyst)):
    """List all registered agent roles and their permitted tools."""
    from app.agents.governance.policy_enforcement import AGENT_PERMISSIONS
    return {
        role.value: [t.value for t in tools]
        for role, tools in AGENT_PERMISSIONS.items()
    }
