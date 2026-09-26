import api, { apiError } from './client'

/** The addresses that are allowed to use admin features. */
export const fetchSuperEmails = async () => {
  try {
    const res = await api.get('/auth/admin/super-emails/')
    return res.data?.results ?? []
  } catch (e) {
    throw new Error(apiError(e, 'Could not load super emails'))
  }
}

export const addSuperEmail = async (email, note) => {
  try {
    const res = await api.post('/auth/admin/super-emails/', { email, note: note || '' })
    return res.data
  } catch (e) {
    throw new Error(apiError(e, 'Could not add that email'))
  }
}

export const setSuperEmailActive = async (id, isActive) => {
  try {
    const res = await api.patch(`/auth/admin/super-emails/${id}/`, { is_active: isActive })
    return res.data
  } catch (e) {
    throw new Error(apiError(e, 'Could not update that email'))
  }
}

export const removeSuperEmail = async (id) => {
  try {
    await api.delete(`/auth/admin/super-emails/${id}/`)
  } catch (e) {
    throw new Error(apiError(e, 'Could not remove that email'))
  }
}

/** The signed-in admin's own address, which is what the list matches on. */
export const fetchMyEmail = async () => {
  try {
    const res = await api.get('/auth/me/email/')
    return res.data?.email ?? ''
  } catch (e) {
    throw new Error(apiError(e, 'Could not load your email'))
  }
}

export const updateMyEmail = async (email) => {
  try {
    const res = await api.patch('/auth/me/email/', { email })
    return res.data
  } catch (e) {
    throw new Error(apiError(e, 'Could not update your email'))
  }
}
