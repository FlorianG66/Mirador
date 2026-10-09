// Contexte d'authentification (phase 3c). Séparé du composant provider pour que
// le module qui exporte un composant ne contienne que des composants (règle
// react-refresh), et pour importer `useAuth` sans tirer le provider.
import { createContext, useContext } from 'react'
import type { MeResponse, MyPermissionsOut } from '../api/types'

export type AuthStatus = 'loading' | 'anonymous' | 'authenticated' | 'error'

export interface AuthContextValue {
  status: AuthStatus
  user: MeResponse | null
  activeOrganizationId: string | null
  permissions: MyPermissionsOut | null
  reload: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

/** Accède au contexte d'auth ; lève si utilisé hors du <AuthProvider>. */
export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (value === null) {
    throw new Error('useAuth doit être utilisé sous <AuthProvider>.')
  }
  return value
}
