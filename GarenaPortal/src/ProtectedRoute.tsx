import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './auth'

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { username } = useAuth()
  const location = useLocation()

  if (!username) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return children
}

export default ProtectedRoute
