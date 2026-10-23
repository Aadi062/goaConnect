import React, { useState } from 'react'
import { useAlerts, useSecurityPosture, useApprovals, useAuditLog, useApprovalDecide } from '../../hooks/useSecurity'
import { SeverityBadge, StatusBadge, ConfidenceMeter, PostureIndicator, MetricCard } from '../shared/Badges'
import { format } from 'date-fns'
import type { SecurityAlert, ApprovalRequest, AuditEvent } from '../../types'

// ──── Alert Row ─────────────────────────────────────────────────
function AlertRow({ alert }: { alert: SecurityAlert }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <>
      <tr
        className="border-b border-slate-800 hover:bg-slate-800/40 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <td className="px-4 py-3">
          <SeverityBadge severity={alert.severity} />
        </td>
        <td className="px-4 py-3 text-sm text-slate-200 max-w-xs truncate">{alert.title}</td>
        <td className="px-4 py-3"><StatusBadge status={alert.status} /></td>
        <td className="px-4 py-3 text-xs text-slate-400 font-mono">{alert.source_agent}</td>
        <td className="px-4 py-3 w-32"><ConfidenceMeter value={alert.confidence} /></td>
        <td className="px-4 py-3 text-xs text-slate-500">
          {format(new Date(alert.created_at), 'HH:mm:ss')}
        </td>
      </tr>
      {expanded && (
        <tr className="bg-slate-900/60">
          <td colSpan={6} className="px-6 py-4 text-sm text-slate-300">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-slate-500 mb-1">DESCRIPTION</p>
                <p>{alert.description}</p>
                {alert.affected_resource && (
                  <p className="mt-2 text-xs text-slate-400">
                    Resource: <span className="font-mono text-slate-200">{alert.affected_resource}</span>
                  </p>
                )}
              </div>
              <div>
                <p className="text-xs text-slate-500 mb-1">VERIFICATION</p>
                <p className={alert.is_verified ? 'text-green-400' : 'text-yellow-400'}>
                  {alert.is_verified
                    ? `✓ Verified by ${alert.verified_by}`
                    : '⚠ Unverified — treat as hypothesis'}
                </p>
                {alert.assigned_to && (
                  <p className="mt-1 text-xs text-slate-400">Assigned: {alert.assigned_to}</p>
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

// ──── Approval Row ───────────────────────────────────────────────
function ApprovalRow({ approval }: { approval: ApprovalRequest }) {
  const decide = useApprovalDecide()
  return (
    <div className="cyber-card border-yellow-700/40 mb-2">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-slate-200">{approval.action_description}</p>
          <p className="text-xs text-slate-400 mt-1">
            Agent: <span className="font-mono">{approval.requesting_agent}</span> ·
            Type: <span className="font-mono">{approval.action_type}</span> ·
            Risk: <span className={`font-mono font-bold ${approval.risk_level === 'high' || approval.risk_level === 'critical' ? 'text-red-400' : 'text-yellow-400'}`}>
              {approval.risk_level}
            </span>
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Expires: {format(new Date(approval.expires_at), 'yyyy-MM-dd HH:mm')}
          </p>
        </div>
        {approval.status === 'pending' && (
          <div className="flex gap-2 ml-4">
            <button
              onClick={() => decide.mutate({ id: approval.id, approved: true })}
              className="px-3 py-1 text-xs bg-green-800 hover:bg-green-700 text-green-200 rounded font-mono"
            >
              APPROVE
            </button>
            <button
              onClick={() => decide.mutate({ id: approval.id, approved: false })}
              className="px-3 py-1 text-xs bg-red-900 hover:bg-red-800 text-red-200 rounded font-mono"
            >
              REJECT
            </button>
          </div>
        )}
        {approval.status !== 'pending' && <StatusBadge status={approval.status} />}
      </div>
    </div>
  )
}

// ──── Audit Log Table ────────────────────────────────────────────
function AuditTable({ events }: { events: AuditEvent[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-slate-500 border-b border-slate-800">
            <th className="px-3 py-2 text-left">Time</th>
            <th className="px-3 py-2 text-left">Type</th>
            <th className="px-3 py-2 text-left">Action</th>
            <th className="px-3 py-2 text-left">Outcome</th>
            <th className="px-3 py-2 text-left">User</th>
            <th className="px-3 py-2 text-left">Resource</th>
          </tr>
        </thead>
        <tbody>
          {events.map(e => (
            <tr key={e.id} className="border-b border-slate-800/50 hover:bg-slate-800/20">
              <td className="px-3 py-2 font-mono text-slate-400">
                {format(new Date(e.created_at), 'HH:mm:ss')}
              </td>
              <td className="px-3 py-2 font-mono text-sky-400">{e.event_type}</td>
              <td className="px-3 py-2 text-slate-300">{e.action}</td>
              <td className="px-3 py-2">
                <span className={e.outcome === 'success' ? 'text-green-400' : e.outcome === 'failure' ? 'text-red-400' : 'text-yellow-400'}>
                  {e.outcome}
                </span>
              </td>
              <td className="px-3 py-2 text-slate-400 font-mono">{e.username || e.user_id?.slice(0, 8) || '—'}</td>
              <td className="px-3 py-2 text-slate-400 truncate max-w-xs">{e.resource || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ──── Main Dashboard ─────────────────────────────────────────────
export default function SecurityDashboard() {
  const [activeTab, setActiveTab] = useState<'alerts' | 'approvals' | 'audit'>('alerts')
  const { data: posture, isLoading: postureLoading } = useSecurityPosture()
  const { data: alertsData, isLoading: alertsLoading } = useAlerts({ page: 1 })
  const { data: approvals } = useApprovals()
  const { data: auditEvents } = useAuditLog()

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-mono font-bold text-emerald-400 tracking-wider">
            ◈ GOACONNECT SECURITY COMMAND CENTRE
          </h1>
          <p className="text-xs text-slate-500 mt-1 font-mono">
            Cybersecurity AI Force · Multi-Agent Defensive Platform
          </p>
        </div>
        <div className="flex items-center gap-6">
          {posture && <PostureIndicator posture={posture.posture} />}
          <span className="text-xs text-slate-500 font-mono">
            {new Date().toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <MetricCard
          label="Open Alerts"
          value={posture?.open_alerts ?? '—'}
          sub="All severities"
          urgent={true}
        />
        <MetricCard
          label="Critical Alerts"
          value={posture?.critical_open_alerts ?? '—'}
          sub="Immediate action"
          urgent={true}
        />
        <MetricCard
          label="Pending Approvals"
          value={posture?.pending_approvals ?? '—'}
          sub="Awaiting review"
          urgent={true}
        />
        <MetricCard
          label="Total Alerts"
          value={alertsData?.total ?? '—'}
          sub="All time"
        />
      </div>

      {/* Disclaimer */}
      <div className="bg-yellow-900/20 border border-yellow-700/40 rounded p-3 mb-6 text-xs text-yellow-300">
        ⚠ AI-generated assessments are marked as hypotheses until independently verified.
        Unverified alerts do not constitute confirmed security incidents.
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-slate-800">
        {(['alerts', 'approvals', 'audit'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-mono uppercase tracking-wider border-b-2 transition-colors ${
              activeTab === tab
                ? 'border-emerald-400 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab === 'alerts' && `Alerts ${alertsData ? `(${alertsData.total})` : ''}`}
            {tab === 'approvals' && `Approvals ${approvals ? `(${approvals.length})` : ''}`}
            {tab === 'audit' && 'Audit Log'}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'alerts' && (
        <div className="cyber-card overflow-hidden p-0">
          {alertsLoading ? (
            <div className="p-8 text-center text-slate-500 font-mono">Loading alerts…</div>
          ) : !alertsData?.items.length ? (
            <div className="p-8 text-center text-green-400 font-mono">
              ✓ No open alerts — system posture clean
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-slate-900">
                <tr className="text-left text-xs text-slate-500 uppercase tracking-wider">
                  <th className="px-4 py-3">Severity</th>
                  <th className="px-4 py-3">Title</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Source Agent</th>
                  <th className="px-4 py-3">Confidence</th>
                  <th className="px-4 py-3">Time</th>
                </tr>
              </thead>
              <tbody>
                {alertsData.items.map(alert => (
                  <AlertRow key={alert.id} alert={alert} />
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {activeTab === 'approvals' && (
        <div>
          {!approvals?.length ? (
            <div className="cyber-card text-center text-slate-400 font-mono">
              ✓ No pending approval requests
            </div>
          ) : (
            approvals.map(a => <ApprovalRow key={a.id} approval={a} />)
          )}
        </div>
      )}

      {activeTab === 'audit' && (
        <div className="cyber-card overflow-hidden p-0">
          {!auditEvents?.length ? (
            <div className="p-8 text-center text-slate-500 font-mono">No audit events yet</div>
          ) : (
            <AuditTable events={auditEvents} />
          )}
        </div>
      )}
    </div>
  )
}
