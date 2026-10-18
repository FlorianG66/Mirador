// Requêtes du centre de notifications (sous-phase 6c-ii). Les queryFn et
// mutations sont séparées des composants (règle react-refresh). Le backend
// calcule la liste personnelle et le compteur de non-lus : le client ne filtre
// rien et se contente d'invalider après chaque marquage (AGENTS.md §8).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, api, unwrap } from '../api/client.ts'
import type { NotificationList } from '../api/types.ts'
import { POLLING_INTERVAL_MS } from '../metrics/queries.ts'

const NOTIFICATIONS_PATH = '/api/v1/organizations/{organization_id}/notifications' as const
const READ_PATH =
  '/api/v1/organizations/{organization_id}/notifications/{notification_id}/read' as const
const READ_ALL_PATH = '/api/v1/organizations/{organization_id}/notifications/read-all' as const

export const notificationsKeys = {
  list: (organizationId: string) => ['notifications', organizationId] as const,
}

export function fetchNotifications(organizationId: string): Promise<NotificationList> {
  return unwrap(
    api.GET(NOTIFICATIONS_PATH, { params: { path: { organization_id: organizationId } } }),
  )
}

export function useNotifications(organizationId: string | null) {
  return useQuery({
    queryKey: notificationsKeys.list(organizationId ?? ''),
    queryFn: () => fetchNotifications(organizationId as string),
    enabled: Boolean(organizationId),
    // Rafraîchissement périodique (comme le Pouls) + après chaque marquage.
    refetchInterval: POLLING_INTERVAL_MS,
    retry: false,
    refetchOnWindowFocus: false,
  })
}

// Contrôle le statut d'une écriture sans corps (204) : `unwrap` attend un JSON,
// donc on attend la réponse de l'appel OpenAPI puis on laisse la mutation
// remonter l'erreur RFC 9457 le cas échéant.
async function expectNoContent(
  result: Promise<{ response: Response; error?: unknown }>,
): Promise<void> {
  const { response, error } = await result
  if (!response.ok) {
    throw ApiError.from(response.status, error)
  }
}

export function useMarkNotificationRead(organizationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (notificationId: string) =>
      expectNoContent(
        api.POST(READ_PATH, {
          params: { path: { organization_id: organizationId, notification_id: notificationId } },
        }),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: notificationsKeys.list(organizationId) }),
  })
}

export function useMarkAllNotificationsRead(organizationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () =>
      expectNoContent(
        api.POST(READ_ALL_PATH, { params: { path: { organization_id: organizationId } } }),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: notificationsKeys.list(organizationId) }),
  })
}
