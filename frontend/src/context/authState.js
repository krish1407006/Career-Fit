import { createContext, useContext } from 'react'

/**
 * The auth context object, kept apart from the provider component.
 *
 * A module that exports both a component and a plain hook only half-reloads
 * during development, so the hook and its context live here and the provider
 * lives in AuthContext.jsx.
 */
export const AuthContext = createContext(null)

export const useAuth = () => useContext(AuthContext)
