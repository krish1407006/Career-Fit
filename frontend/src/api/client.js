import axios from 'axios'

const ACCESS_KEY = 'careerai_access'
const REFRESH_KEY = 'careerai_refresh'
const TOKEN_KEYS = [ACCESS_KEY, REFRESH_KEY]

// Endpoints that own their own 401 responses. Replaying them is either
// pointless (token refresh) or harmful (a retried login would silently
// succeed with a *different* user's tokens).
const AUTH_ENTRY_POINTS = ['/auth/login/', '/auth/register/', '/auth/token/refresh/']

export const getTokens = () => ({
  access: localStorage.getItem(ACCESS_KEY),
  refresh: localStorage.getItem(REFRESH_KEY),
})

export const setTokens = ({ access, refresh }) => {
  if (access) localStorage.setItem(ACCESS_KEY, access)
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
}

export const clearTokens = () => {
  TOKEN_KEYS.forEach((key) => localStorage.removeItem(key))
}

/**
 * Notifies when another browser tab signs out (or clears storage), so the
 * app can drop the in-memory session instead of pretending to be signed in.
 */
export const onTokensCleared = (handler) => {
  const listener = (event) => {
    if (event.key === null || TOKEN_KEYS.includes(event.key)) {
      if (!getTokens().access) handler()
    }
  }
  window.addEventListener('storage', listener)
  return () => window.removeEventListener('storage', listener)
}

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.request.use((config) => {
  const { access } = getTokens()
  if (access) config.headers.Authorization = `Bearer ${access}`
  return config
})

let refreshing = null

const isAuthEntryPoint = (url = '') => AUTH_ENTRY_POINTS.some((path) => url.includes(path))

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error?.config
    const status = error?.response?.status

    // Only 401s are recoverable, and only when axios gave us a request to replay.
    if (status !== 401 || !original) return Promise.reject(error)

    // A rejected login/register must surface its own error without touching
    // the session that may already be stored in this browser.
    if (isAuthEntryPoint(original.url)) return Promise.reject(error)

    const { refresh } = getTokens()
    if (!refresh || original._retried) {
      clearTokens()
      return Promise.reject(error)
    }

    original._retried = true
    refreshing =
      refreshing ||
      axios
        .post('/api/auth/token/refresh/', { refresh })
        .then(({ data }) => {
          // Token rotation is enabled, so prefer the new refresh token but
          // keep the old one if the server did not rotate.
          setTokens({ access: data.access, refresh: data.refresh || refresh })
          return data.access
        })
        .finally(() => {
          refreshing = null
        })

    try {
      const access = await refreshing
      original.headers = { ...original.headers, Authorization: `Bearer ${access}` }
      return client(original)
    } catch {
      // Another tab may have rotated the refresh token while this one was in
      // flight (and a rotated token is then blacklisted). Only drop the
      // session if the token we tried is still the one in storage, otherwise we
      // would delete the fresh tokens the other tab just wrote.
      if (getTokens().refresh === refresh) clearTokens()
      return Promise.reject(error)
    }
  },
)

export const apiError = (error, fallback = 'Something went wrong') => {
  const data = error?.response?.data
  if (!data) return fallback
  if (typeof data === 'string') return data
  if (Array.isArray(data)) return data[0]
  if (data.detail) return data.detail
  if (data.non_field_errors) return data.non_field_errors.join(', ')
  const first = Object.values(data)[0]
  if (Array.isArray(first)) return first[0]
  return fallback
}

export default client
