import React from 'react'
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import SecurityDashboard from './components/security/SecurityDashboard'
import TourismDashboard from './components/tourism/TourismDashboard'
import LoginPage from './pages/LoginPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('access_token')
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

function Nav() {
  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    window.location.href = '/login'
  }
  return (
    <nav className="bg-slate-900 border-b border-slate-800 px-4 py-2 flex items-center gap-6">
      <span className="font-mono text-emerald-400 font-bold text-sm">◈ GoaConnect</span>
      <div className="flex gap-4 flex-1">
        <NavLink
          to="/security"
          className={({ isActive }) =>
            `text-sm font-mono transition-colors ${isActive ? 'text-emerald-400' : 'text-slate-400 hover:text-slate-200'}`
          }
        >
          Security
        </NavLink>
        <NavLink
          to="/tourism"
          className={({ isActive }) =>
            `text-sm font-mono transition-colors ${isActive ? 'text-amber-400' : 'text-slate-400 hover:text-slate-200'}`
          }
        >
          Tourism
        </NavLink>
      </div>
      <button
        onClick={handleLogout}
        className="text-xs text-slate-500 hover:text-slate-300 font-mono"
      >
        LOGOUT
      </button>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <div>
                <Nav />
                <Routes>
                  <Route path="/security" element={<SecurityDashboard />} />
                  <Route path="/tourism" element={<TourismDashboard />} />
                  <Route path="/" element={<Navigate to="/security" replace />} />
                </Routes>
              </div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}
