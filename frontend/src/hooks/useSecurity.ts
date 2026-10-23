import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'
import type {
  AlertListResponse, SecurityPosture, ApprovalRequest,
  AuditEvent, AgentTaskResult
} from '../types'

export function useSecurityPosture() {
  return useQuery<SecurityPosture>({
    queryKey: ['security', 'posture'],
    queryFn: () => api.get('/security/posture').then(r => r.data),
    refetchInterval: 30000,
  })
}

export function useAlerts(params?: { severity?: string; status?: string; page?: number }) {
  return useQuery<AlertListResponse>({
    queryKey: ['security', 'alerts', params],
    queryFn: () => api.get('/security/alerts', { params }).then(r => r.data),
    refetchInterval: 15000,
  })
}

export function useApprovals(status = 'pending') {
  return useQuery<ApprovalRequest[]>({
    queryKey: ['security', 'approvals', status],
    queryFn: () => api.get('/security/approvals', { params: { status } }).then(r => r.data),
    refetchInterval: 10000,
  })
}

export function useAuditLog(params?: { event_type?: string; page?: number }) {
  return useQuery<AuditEvent[]>({
    queryKey: ['security', 'audit', params],
    queryFn: () => api.get('/security/audit', { params }).then(r => r.data),
  })
}

export function useApprovalDecide() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, approved, note }: { id: string; approved: boolean; note?: string }) =>
      api.post(`/security/approvals/${id}/decide`, { approved, note }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['security', 'approvals'] })
      qc.invalidateQueries({ queryKey: ['security', 'posture'] })
    },
  })
}

export function useSubmitAgentTask() {
  return useMutation<AgentTaskResult, Error, { task_type: string; payload: Record<string, unknown> }>({
    mutationFn: (data) => api.post('/agents/tasks', data).then(r => r.data),
  })
}
