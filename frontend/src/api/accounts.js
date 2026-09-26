import api, { apiError } from './client'

/** Every account on the platform, with the records each one owns. Admin only. */
export const fetchAdminUsers = async () => {
  const res = await api.get('/auth/admin/users/')
  return res.data?.results ?? res.data
}

/** Remove several accounts at once. */
export const bulkDeleteAdminUsers = async (ids) => {
  try {
    const res = await api.post('/auth/admin/users/bulk-delete/', { ids })
    return res.data
  } catch (e) {
    throw new Error(apiError(e, 'Could not delete the selected accounts'))
  }
}

/** Toggle an account's active flag so it can or cannot sign in. */
export const setAdminUserActive = async (id, isActive) => {
  try {
    const res = await api.patch(`/auth/admin/users/${id}/`, { is_active: isActive })
    return res.data
  } catch (e) {
    throw new Error(apiError(e, 'Could not update that account'))
  }
}

export { apiError }
