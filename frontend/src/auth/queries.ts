// Requêtes d'authentification TanStack Query (sous-phase 3d-a).
// Sépare les queryFn des composants pour respecter la règle react-refresh.
import { api, ApiError } from '../api/client'
import type { MeResponse, MyPermissionsOut } from '../api/types'

export const authKeys = {
  me: ['auth', 'me'] as const,
  permissions: (organizationId: string) => ['auth', 'permissions', organizationId] as const,
}

export async function fetchMe(): Promise<MeResponse> {
  const result = await api.GET('/api/v1/auth/me')
  if (!result.response.ok) {
    throw ApiError.from(result.response.status, result.error)
  }
  return result.data!
}

export async function fetchPermissions(organizationId: string): Promise<MyPermissionsOut> {
  const result = await api.GET('/api/v1/organizations/{organization_id}/permissions', {
    params: { path: { organization_id: organizationId } },
  })
  if (!result.response.ok) {
    throw ApiError.from(result.response.status, result.error)
  }
  return result.data!
}
