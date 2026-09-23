import axios from 'axios'

const ACCESS_KEY = 'careerai_access'
const REFRESH_KEY = 'careerai_refresh'

export const getTokens = () => ({
  access: localStorage.getItem(ACCESS_KEY),
  refresh: localStorage.getItem(REFRESH_KEY),
})

export const setTokens = ({ access, refresh }) => {
  if (access) localStorage.setItem(ACCESS_KEY, access)
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
}

export const clearTokens = () => {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
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

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const { refresh } = getTokens()
    if (error.response?.status === 401 && refresh && !original._retried) {
      original._retried = true
      refreshing = refreshing || axios.post('/api/auth/token/refresh/', { refresh })
        .then(({ data }) => {
          setTokens({ access: data.access, refresh: data.refresh })
          return data.access
        })
        .finally(() => { refreshing = null })
      try {
        const access = await refreshing
        original.headers.Authorization = `Bearer ${access}`
        return client(original)
      } catch {
        clearTokens()
      }
    }
    if (error.response?.status === 401) clearTokens()
    return Promise.reject(error)
  },
)

export const apiError = (error, fallback = 'Something went wrong') => {
  const data = error?.response?.data
  if (!data) return fallback
  if (typeof data === 'string') return data
  if (data.detail) return data.detail
  if (data.non_field_errors) return data.non_field_errors.join(', ')
  const first = Object.values(data)[0]
  if (Array.isArray(first)) return first[0]
  return fallback
}

export default client