import { createContext, useContext, useState, type ReactNode } from 'react'

const STORAGE_KEY = 'garena-username'

interface AuthContextValue {
  username: string | null
  login: (username: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [username, setUsername] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY))

  function login(name: string) {
    localStorage.setItem(STORAGE_KEY, name)
    setUsername(name)
  }

  function logout() {
    localStorage.removeItem(STORAGE_KEY)
    setUsername(null)
  }

  return <AuthContext.Provider value={{ username, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
