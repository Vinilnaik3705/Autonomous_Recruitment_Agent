import { useState } from 'react'
import { AuthProvider, useAuth } from './context/AuthContext'
import HRScreening from './components/HRScreening'
import InterviewStatus from './components/InterviewStatus'
import CandidatePortal from './components/CandidatePortal'
import Login from './components/Login'
import Landing from './components/Landing'

function AppContent() {
  const { isAuthenticated, user } = useAuth()
  const oauthHash = typeof window !== 'undefined' ? window.location.hash || '' : ''
  const hasGoogleOauthCallback = oauthHash.includes('access_token=') || oauthHash.includes('error=')

  // Show public landing page at root path regardless of auth state
  if (typeof window !== 'undefined' && window.location.pathname === '/') {
    if (hasGoogleOauthCallback) {
      return <Login />
    }
    return <Landing />
  }

  // Always show Login when visiting /login so Sign In opens the login form
  if (typeof window !== 'undefined' && window.location.pathname === '/login') {
    return <Login />
  }

  // If user is not authenticated, show the login page for other routes
  if (!isAuthenticated) return <Login />

  const role = user?.role

  if (role === 'candidate') return <CandidatePortal />
  if (role === 'interviewer') return <InterviewStatus />
  // recruiter, super_admin → full HR panel
  return <HRScreening />
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

export default App
