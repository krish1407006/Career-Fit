/**
 * Client-side checks for the self-service password change form.
 *
 * These are a fast, friendly pre-check only: the server re-validates the
 * current password and runs Django's password validators regardless, so this
 * never stands in for the backend rules.
 */

export const MIN_PASSWORD_LENGTH = 8

export const validatePasswordChange = ({ current_password, new_password, confirm }) => {
  if (!current_password) return 'Enter your current password.'
  if (!new_password) return 'Enter a new password.'
  if (new_password.length < MIN_PASSWORD_LENGTH) {
    return `New password must be at least ${MIN_PASSWORD_LENGTH} characters.`
  }
  if (new_password !== confirm) return 'New passwords do not match.'
  if (new_password === current_password) {
    return 'New password must differ from your current password.'
  }
  return ''
}
