import React, { useState } from 'react'
import api from '../lib/api'
import type { TokenResponse } from '../types'

export default function LoginPage() {
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.post<TokenResponse>('/auth/login', form)
      localStorage.setItem('access_token', res.data.access_token)
      localStorage.setItem('refresh_token', res.data.refresh_token)
      window.location.href = '/'
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-mono font-bold text-emerald-400">◈ GOACONNECT</h1>
          <p className="text-slate-500 text-sm mt-1">Cybersecurity AI Force</p>
        </div>
        <form onSubmit={handleSubmit} className="cyber-card space-y-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1 uppercase tracking-wider">Username</label>
            <input
              className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-slate-100 focus:outline-none focus:border-emerald-500 font-mono"
              value={form.username}
              onChange={e => setForm({ ...form, username: e.target.value })}
              required
              autoComplete="username"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1 uppercase tracking-wider">Password</label>
            <input
              type="password"
              className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-slate-100 focus:outline-none focus:border-emerald-500 font-mono"
              value={form.password}
              onChange={e => setForm({ ...form, password: e.target.value })}
              required
              autoComplete="current-password"
            />
          </div>
          {error && (
            <div className="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded p-2">{error}</div>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-white rounded font-mono font-medium transition-colors"
          >
            {loading ? 'AUTHENTICATING…' : 'LOGIN'}
          </button>
        </form>
        <p className="text-center text-xs text-slate-600 mt-4">
          All access is logged · Unauthorized access is prohibited
        </p>
      </div>
    </div>
  )
}
