import { createContext, useContext, useEffect, useState } from 'react'
import { clearTokens, getTokens, onTokensCleared } from '../api/client'
import {
  fetchMe,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
  updateMe,
} from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(Boolean(getTokens().access))

  const refreshUser = async () => {
    const data = await fetchMe()
    setUser(data.user)
    setProfile(data.profile || null)
    return data
  }

  useEffect(() => {
    if (!getTokens().access) return
    refreshUser()
      .catch(() => clearTokens())
      .finally(() => setLoading(false))
  }, [])

  // Signing out in another tab clears the shared token storage; drop the
  // in-memory session instead of leaving a stale, unusable user object.
  useEffect(
    () =>
      onTokensCleared(() => {
        setUser(null)
        setProfile(null)
        setLoading(false)
      }),
    [],
  )

  const login = async (credentials) => {
    const u = await apiLogin(credentials)
    setUser(u)
    await refreshUser()
    return u
  }

  const register = async (payload) => {
    await apiRegister(payload)
  }

  const logout = async () => {
    try {
      await apiLogout()
    } finally {
      clearTokens()
      setUser(null)
      setProfile(null)
    }
  }

  const updateProfile = async (payload) => {
    await updateMe(payload)
    return refreshUser()
  }

  const value = {
    user,
    profile,
    loading,
    login,
    register,
    logout,
    refreshUser,
    updateProfile,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)