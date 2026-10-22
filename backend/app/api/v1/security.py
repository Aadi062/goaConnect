"""Security API: alerts, audit log, approval workflow, health posture."""
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.deps import get_current_user, require_security, require_analyst
from app.db.models.user import User
from app.db.models.security import (
    SecurityAlert, SecurityIncident, HumanApprovalRequest,
    AuditEvent, AlertSeverity, AlertStatus,
)
from app.schemas.security import (
    SecurityAlertCreate, SecurityAlertOut, SecurityAlertUpdate,
    AlertListResponse, ApprovalRequestCreate, ApprovalRequestOut, ApprovalDecision,
    AuditEventOut,
)
from app.services.security.alert_service import create_alert, get_alerts, update_alert
from app.services.security.audit import log_event

router = APIRouter(prefix="/security", tags=["security"])


# ─────────────────────────── Alerts ────────────────────────────

@router.post("/alerts", response_model=SecurityAlertOut, status_code=status.HTTP_201_CREATED)
async def create_security_alert(
    data: SecurityAlertCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_security),
):
    alert = await create_alert(db, data, raised_by_user_id=current_user.id)
    return alert


@router.get("/alerts", response_model=AlertListResponse)
async def list_alerts(
    severity: Optional[AlertSeverity] = Query(default=None),
    status_filter: Optional[AlertStatus] = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    items, total = await get_alerts(db, severity=severity, status=status_filter, page=page, page_size=page_size)
    return AlertListResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/alerts/{alert_id}", response_model=SecurityAlertOut)
async def get_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    result = await db.execute(select(SecurityAlert).where(SecurityAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.patch("/alerts/{alert_id}", response_model=SecurityAlertOut)
async def patch_alert(
    alert_id: str,
    update: SecurityAlertUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_security),
):
    alert = await update_alert(db, alert_id, update, updated_by_user_id=current_user.id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


# ─────────────────────────── Audit Log ─────────────────────────

@router.get("/audit", response_model=list[AuditEventOut])
async def list_audit_events(
    event_type: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_security),
):
    query = select(AuditEvent)
    if event_type:
        query = query.where(AuditEvent.event_type == event_type)
    if user_id:
        query = query.where(AuditEvent.user_id == user_id)
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(AuditEvent.created_at.desc()).offset(offset).limit(page_size)
    )
    return result.scalars().all()


# ─────────────────────── Human Approval ──────────────────────

@router.post("/approvals", response_model=ApprovalRequestOut, status_code=status.HTTP_201_CREATED)
async def request_approval(
    data: ApprovalRequestCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_security),
):
    approval = HumanApprovalRequest(
        id=str(uuid.uuid4()),
        requesting_agent=data.requesting_agent,
        action_type=data.action_type,
        action_description=data.action_description,
        action_payload=data.action_payload,
        risk_level=data.risk_level,
        status="pending",
        requested_by_user=current_user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=data.expires_in_minutes),
    )
    db.add(approval)
    await db.flush()

    await log_event(
        db, "security.approval.requested", "request_approval", "success",
        user_id=current_user.id, resource=f"approval:{approval.id}",
        detail={"action_type": data.action_type, "risk_level": data.risk_level},
    )
    return approval


@router.get("/approvals", response_model=list[ApprovalRequestOut])
async def list_approvals(
    status_filter: Optional[str] = Query(default="pending", alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_security),
):
    query = select(HumanApprovalRequest)
    if status_filter:
        query = query.where(HumanApprovalRequest.status == status_filter)
    result = await db.execute(
        query.order_by(HumanApprovalRequest.created_at.desc()).limit(100)
    )
    return result.scalars().all()


@router.post("/approvals/{approval_id}/decide", response_model=ApprovalRequestOut)
async def decide_approval(
    approval_id: str,
    decision: ApprovalDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_security),
):
    result = await db.execute(
        select(HumanApprovalRequest).where(HumanApprovalRequest.id == approval_id)
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if approval.status != "pending":
        raise HTTPException(status_code=409, detail=f"Already in status: {approval.status}")

    now = datetime.now(timezone.utc)
    expires = approval.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        approval.status = "expired"
        raise HTTPException(status_code=410, detail="Approval request has expired")

    # An agent cannot approve its own request (checked by role + user — not same agent)
    approval.status = "approved" if decision.approved else "rejected"
    approval.approved_by_user = current_user.id
    approval.approval_note = decision.note
    approval.actioned_at = datetime.now(timezone.utc)

    await log_event(
        db, "security.approval.decided", "decide_approval",
        "approved" if decision.approved else "rejected",
        user_id=current_user.id, resource=f"approval:{approval_id}",
        detail={"approved": decision.approved, "note": decision.note},
    )
    return approval


# ─────────────────────── Security Posture ────────────────────

@router.get("/posture")
async def security_posture(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """High-level security posture snapshot for the dashboard."""
    open_count = (await db.execute(
        select(func.count(SecurityAlert.id)).where(SecurityAlert.status == "open")
    )).scalar_one()
    critical_count = (await db.execute(
        select(func.count(SecurityAlert.id)).where(
            SecurityAlert.severity == "critical", SecurityAlert.status == "open"
        )
    )).scalar_one()
    pending_approvals = (await db.execute(
        select(func.count(HumanApprovalRequest.id)).where(
            HumanApprovalRequest.status == "pending"
        )
    )).scalar_one()

    return {
        "open_alerts": open_count,
        "critical_open_alerts": critical_count,
        "pending_approvals": pending_approvals,
        "posture": "critical" if critical_count > 0 else ("warning" if open_count > 0 else "healthy"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
