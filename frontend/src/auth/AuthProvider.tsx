// Fournisseur d'authentification (sous-phase 3d-a) : récupère la session
// (`/auth/me`), choisit l'organisation active (mémorisée si valide, sinon la
// première) et charge ses permissions via TanStack Query. Les gardes de routes
// consomment ce contexte.
import { useCallback, useMemo } from 'react'
import { Outlet } from 'react-router'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { MembershipOut } from '../api/types'
import { AuthContext, type AuthContextValue, type AuthStatus } from './context'
import { authKeys, fetchMe, fetchPermissions } from './queries'

export const ACTIVE_ORGANIZATION_KEY = 'mirador.organizationId'

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

export function AuthProvider() {
  const queryClient = useQueryClient()

  const meQuery = useQuery({
    queryKey: authKeys.me,
    queryFn: fetchMe,
  })

  const activeOrganizationId = useMemo(
    () => pickOrganization(meQuery.data?.memberships ?? []),
    [meQuery.data?.memberships],
  )

  const permissionsQuery = useQuery({
    queryKey: authKeys.permissions(activeOrganizationId ?? ''),
    queryFn: () => fetchPermissions(activeOrganizationId!),
    enabled: activeOrganizationId !== null,
  })

  const status: AuthStatus = useMemo(() => {
    if (meQuery.isPending) return 'loading'
    if (meQuery.isError) return 'anonymous'
    if (activeOrganizationId === null) return 'authenticated'
    if (permissionsQuery.isPending) return 'loading'
    if (permissionsQuery.isError) return 'error'
    return 'authenticated'
  }, [meQuery.isPending, meQuery.isError, activeOrganizationId, permissionsQuery.isPending, permissionsQuery.isError])

  const reload = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: authKeys.me })
  }, [queryClient])

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user: meQuery.data ?? null,
      activeOrganizationId,
      permissions: permissionsQuery.data ?? null,
      reload,
    }),
    [status, meQuery.data, activeOrganizationId, permissionsQuery.data, reload],
  )

  return (
    <AuthContext.Provider value={value}>
      <Outlet />
    </AuthContext.Provider>
  )
}
