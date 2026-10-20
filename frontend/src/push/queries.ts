// Requêtes des abonnements Web Push (sous-phase 6c-iii-b). Les queryFn et
// mutations vivent hors des composants (règle react-refresh). La clé VAPID
// publique vient de l'API ; les abonnements sont personnels à l'appelant, il n'y
// a donc pas de liste à interroger côté serveur (l'état vit dans le navigateur).
import { ApiError, api, unwrap } from '../api/client.ts'
import type { PushSubscribe, PushSubscriptionOut } from '../api/types.ts'

const PUBLIC_KEY_PATH = '/api/v1/organizations/{organization_id}/push/public-key' as const
const SUBSCRIPTIONS_PATH =
  '/api/v1/organizations/{organization_id}/push/subscriptions' as const

/** Clé VAPID publique du serveur, ou `null` si le Web Push n'y est pas configuré. */
export async function fetchPushPublicKey(organizationId: string): Promise<string | null> {
  const result = await api.GET(PUBLIC_KEY_PATH, {
    params: { path: { organization_id: organizationId } },
  })
  // 404 = Web Push non configuré : ce n'est pas une erreur, juste un canal absent.
  if (result.response.status === 404) return null
  if (!result.response.ok) {
    throw ApiError.from(result.response.status, result.error)
  }
  return result.data?.public_key ?? null
}

/** Enregistre l'abonnement du navigateur auprès du serveur (idempotent). */
export function postSubscription(
  organizationId: string,
  payload: PushSubscribe,
): Promise<PushSubscriptionOut> {
  return unwrap(
    api.POST(SUBSCRIPTIONS_PATH, {
      params: { path: { organization_id: organizationId } },
      body: payload,
    }),
  )
}

/** Retire un abonnement côté serveur (204 sans corps : on contrôle le statut seul). */
export async function deleteSubscription(
  organizationId: string,
  endpoint: string,
): Promise<void> {
  const result = await api.DELETE(SUBSCRIPTIONS_PATH, {
    params: { path: { organization_id: organizationId } },
    body: { endpoint },
  })
  if (!result.response.ok) {
    throw ApiError.from(result.response.status, result.error)
  }
}
