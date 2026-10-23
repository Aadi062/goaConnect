import React from 'react'
import type { Severity, AlertStatus } from '../../types'

export function SeverityBadge({ severity }: { severity: Severity }) {
  const cls: Record<Severity, string> = {
    critical: 'bg-purple-900/40 text-purple-300 border border-purple-600',
    high:     'bg-red-900/40 text-red-300 border border-red-600',
    medium:   'bg-orange-900/40 text-orange-300 border border-orange-600',
    low:      'bg-yellow-900/40 text-yellow-300 border border-yellow-600',
    info:     'bg-sky-900/40 text-sky-300 border border-sky-600',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono uppercase ${cls[severity]}`}>
      {severity}
    </span>
  )
}

export function StatusBadge({ status }: { status: AlertStatus | string }) {
  const cls: Record<string, string> = {
    open:          'text-red-400',
    investigating: 'text-yellow-400',
    contained:     'text-orange-400',
    resolved:      'text-green-400',
    false_positive:'text-slate-400',
    pending:       'text-yellow-400',
    approved:      'text-green-400',
    rejected:      'text-red-400',
    expired:       'text-slate-500',
  }
  return (
    <span className={`text-xs font-mono uppercase ${cls[status] || 'text-slate-400'}`}>
      ● {status.replace('_', ' ')}
    </span>
  )
}

export function ConfidenceMeter({ value }: { value?: number }) {
  if (value == null) return <span className="text-slate-500 text-xs">N/A</span>
  const pct = Math.round(value * 100)
  const color = pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-slate-700 rounded h-1.5">
        <div className={`${color} h-1.5 rounded`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-400 font-mono w-8 text-right">{pct}%</span>
    </div>
  )
}

export function PostureIndicator({ posture }: { posture: 'healthy' | 'warning' | 'critical' }) {
  const config = {
    healthy: { color: 'text-green-400', dot: 'bg-green-400', label: 'HEALTHY' },
    warning: { color: 'text-yellow-400', dot: 'bg-yellow-400', label: 'WARNING' },
    critical: { color: 'text-red-400', dot: 'bg-red-400 animate-pulse', label: 'CRITICAL' },
  }
  const c = config[posture]
  return (
    <div className={`flex items-center gap-2 ${c.color}`}>
      <span className={`w-2.5 h-2.5 rounded-full ${c.dot}`} />
      <span className="text-sm font-mono font-bold">{c.label}</span>
    </div>
  )
}

export function MetricCard({ label, value, sub, urgent }: {
  label: string; value: string | number; sub?: string; urgent?: boolean
}) {
  return (
    <div className={`cyber-card ${urgent && Number(value) > 0 ? 'border-red-700/60' : ''}`}>
      <p className="text-xs text-slate-400 uppercase tracking-wider">{label}</p>
      <p className={`text-3xl font-mono font-bold mt-1 ${urgent && Number(value) > 0 ? 'text-red-400' : 'text-slate-100'}`}>
        {value}
      </p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  )
}
