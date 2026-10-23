// API types matching backend Pydantic schemas

export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info'
export type AlertStatus = 'open' | 'investigating' | 'contained' | 'resolved' | 'false_positive'

export interface SecurityAlert {
  id: string
  title: string
  description: string
  severity: Severity
  status: AlertStatus
  alert_type: string
  source_agent: string
  affected_resource?: string
  confidence?: number
  is_verified: boolean
  verified_by?: string
  assigned_to?: string
  incident_id?: string
  created_at: string
  updated_at: string
}

export interface AlertListResponse {
  total: number
  page: number
  page_size: number
  items: SecurityAlert[]
}

export interface SecurityPosture {
  open_alerts: number
  critical_open_alerts: number
  pending_approvals: number
  posture: 'healthy' | 'warning' | 'critical'
  timestamp: string
}

export interface ApprovalRequest {
  id: string
  requesting_agent: string
  action_type: string
  action_description: string
  risk_level: string
  status: 'pending' | 'approved' | 'rejected' | 'expired'
  expires_at: string
  created_at: string
  actioned_at?: string
  approved_by_user?: string
  approval_note?: string
}

export interface AuditEvent {
  id: string
  event_type: string
  user_id?: string
  username?: string
  ip_address?: string
  resource?: string
  action: string
  outcome: string
  detail?: Record<string, unknown>
  agent_id?: string
  created_at: string
}

export interface User {
  id: string
  email: string
  username: string
  role: string
  is_active: boolean
  is_verified: boolean
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface Place {
  id: string
  name: string
  name_konkani?: string
  category: string
  description?: string
  latitude?: number
  longitude?: number
  district?: string
  tags?: string[]
  is_verified: boolean
  source_citations?: string[]
}

export interface AgentTaskResult {
  task_id: string
  agent_id: string
  agent_role: string
  status: string
  result?: Record<string, unknown>
  confidence: number
  evidence: Array<Record<string, unknown>>
  reasoning?: string
  requires_human_approval: boolean
  audit_trail: string[]
  completed_at: string
}
