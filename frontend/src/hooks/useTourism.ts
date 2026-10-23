import { useQuery, useMutation } from '@tanstack/react-query'
import api from '../lib/api'
import type { Place, AgentTaskResult } from '../types'

export function usePlaces(params?: { q?: string; category?: string; district?: string }) {
  return useQuery<Place[]>({
    queryKey: ['tourism', 'places', params],
    queryFn: () => api.get('/tourism/places', { params }).then(r => r.data),
  })
}

export function useTravelAssistant() {
  return useMutation<AgentTaskResult, Error, { task_type: string; payload: Record<string, unknown> }>({
    mutationFn: (data) => api.post('/agents/tasks', data).then(r => r.data),
  })
}
