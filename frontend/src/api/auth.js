import client, { getTokens, setTokens } from './client'

export const register = (payload) =>
  client.post('/auth/register/', payload).then(({ data }) => data)

export const login = async (credentials) => {
  const { data } = await client.post('/auth/login/', credentials)
  setTokens({ access: data.access, refresh: data.refresh })
  return data.user
}

export const logout = async () => {
  const { refresh } = getTokens()
  try {
    await client.post('/auth/logout/', { refresh })
  } catch {
    // Blacklisting is best-effort; the client clears tokens regardless.
  }
}

export const fetchMe = () => client.get('/auth/me/').then(({ data }) => data)

export const updateMe = (payload) => client.put('/auth/me/', payload).then(({ data }) => data)

export const fetchAdminUsers = () =>
  client.get('/auth/admin/users/').then(({ data }) => (Array.isArray(data) ? data : data.results || []))