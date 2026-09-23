import client, { setTokens } from './client'

export const register = (payload) =>
  client.post('/auth/register/', payload).then(({ data }) => data)

export const login = async (credentials) => {
  const { data } = await client.post('/auth/token/', credentials)
  setTokens({ access: data.access, refresh: data.refresh })
  return data.user
}

export const fetchMe = () => client.get('/auth/me/').then(({ data }) => data)

export const updateMe = (payload) => client.put('/auth/me/', payload).then(({ data }) => data)