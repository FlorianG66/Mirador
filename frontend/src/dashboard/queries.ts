// Requêtes de la mise en page du tableau de bord (sous-phase 6b-ii-b). Les
// queryFn/mutations sont séparées des composants (règle react-refresh). La
// disposition est personnelle et stockée côté backend : le PUT renvoie l'état
// enregistré (on le pose dans le cache), le DELETE restaure la disposition par
// défaut (on invalide pour relire).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, api, unwrap } from '../api/client.ts'
import type { Dashboard, DashboardLayoutUpdate } from '../api/types.ts'

const DASHBOARD_PATH = '/api/v1/organizations/{organization_id}/dashboard' as const

export const dashboardKeys = {
  layout: (organizationId: string) => ['dashboard', organizationId] as const,
}

export function fetchDashboard(organizationId: string): Promise<Dashboard> {
  return unwrap(
    api.GET(DASHBOARD_PATH, { params: { path: { organization_id: organizationId } } }),
  )
}

export function useDashboard(organizationId: string) {
  return useQuery({
    queryKey: dashboardKeys.layout(organizationId),
    queryFn: () => fetchDashboard(organizationId),
    enabled: Boolean(organizationId),
    retry: false,
    refetchOnWindowFocus: false,
  })
}

export function useSaveDashboard(organizationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: DashboardLayoutUpdate) =>
      unwrap(
        api.PUT(DASHBOARD_PATH, {
          params: { path: { organization_id: organizationId } },
          body: payload,
        }),
      ),
    onSuccess: (data) => queryClient.setQueryData(dashboardKeys.layout(organizationId), data),
  })
}

export function useResetDashboard(organizationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      // 204 sans corps : `unwrap` ne convient pas, on contrôle le statut seul.
      const result = await api.DELETE(DASHBOARD_PATH, {
        params: { path: { organization_id: organizationId } },
      })
      if (!result.response.ok) {
        throw ApiError.from(result.response.status, result.error)
      }
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: dashboardKeys.layout(organizationId) }),
  })
}
