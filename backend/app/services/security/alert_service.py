"""
Alert management service — create, list, update security alerts.
Enforces that confidence is always stored (agents must supply it).
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.security import SecurityAlert, AlertStatus, AlertSeverity
from app.schemas.security import SecurityAlertCreate, SecurityAlertUpdate
from app.services.security.audit import log_event
from app.core.logging import get_logger

logger = get_logger("alert_service")


async def create_alert(
    db: AsyncSession,
    data: SecurityAlertCreate,
    raised_by_user_id: Optional[str] = None,
) -> SecurityAlert:
    alert = SecurityAlert(
        id=str(uuid.uuid4()),
        **data.model_dump(),
    )
    db.add(alert)
    await db.flush()

    await log_event(
        db,
        event_type="security.alert.created",
        action="create_alert",
        outcome="success",
        user_id=raised_by_user_id,
        resource=f"alert:{alert.id}",
        detail={
            "title": alert.title,
            "severity": alert.severity,
            "source_agent": alert.source_agent,
        },
        agent_id=data.source_agent,
    )
    logger.warning(
        "new_security_alert",
        alert_id=alert.id,
        severity=alert.severity,
        title=alert.title,
        source=alert.source_agent,
    )
    return alert


async def get_alerts(
    db: AsyncSession,
    *,
    severity: Optional[AlertSeverity] = None,
    status: Optional[AlertStatus] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[SecurityAlert], int]:
    query = select(SecurityAlert)
    count_query = select(func.count(SecurityAlert.id))
    if severity:
        query = query.where(SecurityAlert.severity == severity)
        count_query = count_query.where(SecurityAlert.severity == severity)
    if status:
        query = query.where(SecurityAlert.status == status)
        count_query = count_query.where(SecurityAlert.status == status)

    total = (await db.execute(count_query)).scalar_one()
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(SecurityAlert.created_at.desc()).offset(offset).limit(page_size)
    )
    return result.scalars().all(), total


async def update_alert(
    db: AsyncSession,
    alert_id: str,
    update: SecurityAlertUpdate,
    updated_by_user_id: Optional[str] = None,
) -> Optional[SecurityAlert]:
    result = await db.execute(
        select(SecurityAlert).where(SecurityAlert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        return None

    for field, value in update.model_dump(exclude_none=True).items():
        setattr(alert, field, value)
    alert.updated_at = datetime.now(timezone.utc)

    await log_event(
        db,
        event_type="security.alert.updated",
        action="update_alert",
        outcome="success",
        user_id=updated_by_user_id,
        resource=f"alert:{alert_id}",
        detail=update.model_dump(exclude_none=True),
    )
    return alert
