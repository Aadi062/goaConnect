"""
Audit logging service — append-only writes to audit.audit_events.
Used by all routes, agents, and services. Never delete from this table.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.security import AuditEvent
from app.core.logging import get_logger

logger = get_logger("audit")


async def log_event(
    db: AsyncSession,
    event_type: str,
    action: str,
    outcome: str,
    *,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    ip_address: Optional[str] = None,
    resource: Optional[str] = None,
    detail: Optional[dict] = None,
    request_id: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> AuditEvent:
    """
    Write one immutable audit record. Commits immediately (uses its own flush).
    Caller's session commit is still required to persist other changes.
    """
    event = AuditEvent(
        id=str(uuid.uuid4()),
        event_type=event_type,
        user_id=user_id,
        username=username,
        ip_address=ip_address,
        resource=resource,
        action=action,
        outcome=outcome,
        detail=detail,
        request_id=request_id,
        agent_id=agent_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    await db.flush()

    logger.info(
        "audit_event",
        event_type=event_type,
        action=action,
        outcome=outcome,
        user_id=user_id,
        resource=resource,
        agent_id=agent_id,
    )
    return event
