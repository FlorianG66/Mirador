// Fournisseur d'authentification (phase 3c) : récupère la session (`/auth/me`),
// choisit l'organisation active (mémorisée si valide, sinon la première) et
// charge ses permissions. Les gardes de routes consomment ce contexte.
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Outlet } from 'react-router'
import { api } from '../api/client'
import type { MeResponse, MembershipOut, MyPermissionsOut } from '../api/types'
import { AuthContext, type AuthContextValue, type AuthStatus } from './context'

export const ACTIVE_ORGANIZATION_KEY = 'mirador.organizationId'

interface AuthState {
  status: AuthStatus
  user: MeResponse | null
  activeOrganizationId: string | null
  permissions: MyPermissionsOut | null
}

const INITIAL_STATE: AuthState = {
  status: 'loading',
  user: null,
  activeOrganizationId: null,
  permissions: null,
}

// Organisation active : celle mémorisée si l'utilisateur en est encore membre,
// sinon la première de la liste (persistée pour les prochaines visites).
function pickOrganization(memberships: MembershipOut[]): string | null {
  const stored = localStorage.getItem(ACTIVE_ORGANIZATION_KEY)
  if (stored !== null && memberships.some((m) => m.organization_id === stored)) {
    return stored
  }
  const first = memberships[0]?.organization_id ?? null
  if (first !== null) {
    localStorage.setItem(ACTIVE_ORGANIZATION_KEY, first)
  }
  return first
}

async function loadPermissions(organizationId: string): Promise<MyPermissionsOut | null> {
  const result = await api.GET('/api/v1/organizations/{organization_id}/permissions', {
    params: { path: { organization_id: organizationId } },
  })
  if (!result.response.ok || !result.data) {
    return null
  }
  return result.data
}

// Charge l'état complet. Une absence de session (401) ou une panne réseau de
// `/auth/me` sont traitées comme un visiteur anonyme ; un échec des permissions
// (session valide) donne un état rechargeable.
async function loadAuthState(): Promise<AuthState> {
  let me: MeResponse
  try {
    const result = await api.GET('/api/v1/auth/me')
    if (!result.response.ok || !result.data) {
      return { ...INITIAL_STATE, status: 'anonymous' }
    }
    me = result.data
  } catch {
    return { ...INITIAL_STATE, status: 'anonymous' }
  }

  const activeOrganizationId = pickOrganization(me.memberships)
  if (activeOrganizationId === null) {
    return { status: 'authenticated', user: me, activeOrganizationId, permissions: null }
  }

  try {
    const permissions = await loadPermissions(activeOrganizationId)
    if (permissions === null) {
      return { status: 'error', user: me, activeOrganizationId, permissions: null }
    }
    return { status: 'authenticated', user: me, activeOrganizationId, permissions }
  } catch {
    return { status: 'error', user: me, activeOrganizationId, permissions: null }
  }
}

export function AuthProvider() {
  const [state, setState] = useState<AuthState>(INITIAL_STATE)

  const reload = useCallback(async () => {
    setState((current) => ({ ...current, status: 'loading' }))
    setState(await loadAuthState())
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  const value = useMemo<AuthContextValue>(() => ({ ...state, reload }), [state, reload])

  return (
    <AuthContext.Provider value={value}>
      <Outlet />
    </AuthContext.Provider>
  )
}
