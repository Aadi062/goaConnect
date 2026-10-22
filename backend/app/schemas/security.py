"""Pydantic schemas for security events, alerts, and approvals."""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field
from app.db.models.security import AlertSeverity, AlertStatus


class AuditEventCreate(BaseModel):
    event_type: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    ip_address: Optional[str] = None
    resource: Optional[str] = None
    action: str
    outcome: str  # success / failure / blocked
    detail: Optional[dict] = None
    request_id: Optional[str] = None
    agent_id: Optional[str] = None


class AuditEventOut(AuditEventCreate):
    id: str
    created_at: datetime
    model_config = {"from_attributes": True}


class SecurityAlertCreate(BaseModel):
    title: str = Field(max_length=500)
    description: str
    severity: AlertSeverity
    alert_type: str = Field(max_length=100)
    source_agent: str = Field(max_length=100)
    affected_resource: Optional[str] = None
    raw_evidence: Optional[dict] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class SecurityAlertOut(SecurityAlertCreate):
    id: str
    status: AlertStatus
    is_verified: bool
    verified_by: Optional[str]
    assigned_to: Optional[str]
    incident_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class SecurityAlertUpdate(BaseModel):
    status: Optional[AlertStatus] = None
    assigned_to: Optional[str] = None
    incident_id: Optional[str] = None
    false_positive_reason: Optional[str] = None
    is_verified: Optional[bool] = None
    verified_by: Optional[str] = None


class AlertListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[SecurityAlertOut]


class ApprovalRequestCreate(BaseModel):
    requesting_agent: str
    action_type: str
    action_description: str
    action_payload: Optional[dict] = None
    risk_level: str = Field(pattern=r"^(low|medium|high|critical)$")
    expires_in_minutes: int = Field(default=60, ge=1, le=1440)


class ApprovalRequestOut(ApprovalRequestCreate):
    id: str
    status: str
    requested_by_user: Optional[str]
    approved_by_user: Optional[str]
    approval_note: Optional[str]
    expires_at: datetime
    created_at: datetime
    actioned_at: Optional[datetime]
    model_config = {"from_attributes": True}


class ApprovalDecision(BaseModel):
    approved: bool
    note: Optional[str] = Field(default=None, max_length=1000)
