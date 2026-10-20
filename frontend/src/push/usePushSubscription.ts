// Hook d'activation des notifications Web Push (sous-phase 6c-iii-b). Il fait le
// lien entre le navigateur (permission, abonnement) et le serveur (clé publique,
// enregistrement de l'abonnement). L'abonnement est personnel : tout membre peut
// l'activer pour lui-même, aucun droit de module n'est requis.
//
// Machine à états simple : `unsupported` (navigateur sans Web Push), `loading`,
// `disabled` (possible mais inactif), `enabled`, `denied` (permission refusée par
// l'utilisateur) et `unavailable` (serveur sans clé VAPID). Aucune donnée réelle.
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/context.ts'
import { deleteSubscription, fetchPushPublicKey, postSubscription } from './queries.ts'
import {
  getSubscription,
  subscribeToPush,
  supportsPush,
  unsubscribeFromPush,
} from './register.ts'

export type PushStatus =
  | 'unsupported'
  | 'loading'
  | 'disabled'
  | 'enabled'
  | 'denied'
  | 'unavailable'

export interface PushSubscriptionState {
  status: PushStatus
  busy: boolean
  error: string | null
  enable: () => Promise<void>
  disable: () => Promise<void>
}

/**
 * État et actions du réglage Web Push pour l'organisation active.
 *
 * `enabled` ne signifie pas « abonné à la seconde » : le navigateur peut révoquer
 * l'abonnement à tout moment. On relit donc l'état réel à chaque montage, et on
 * traite une hausse au serveur comme un simple échec affiché (jamais un crash).
 */
export function usePushSubscription(): PushSubscriptionState {
  const { t } = useTranslation()
  const { activeOrganizationId } = useAuth()
  const [status, setStatus] = useState<PushStatus>('loading')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!supportsPush()) {
      setStatus('unsupported')
      return
    }
    if (Notification.permission === 'denied') {
      setStatus('denied')
      return
    }
    let subscribed: boolean
    try {
      subscribed = (await getSubscription()) !== null
    } catch {
      subscribed = false
    }
    if (subscribed) {
      setStatus('enabled')
      return
    }
    if (activeOrganizationId === null) {
      setStatus('disabled')
      return
    }
    try {
      const key = await fetchPushPublicKey(activeOrganizationId)
      setStatus(key === null ? 'unavailable' : 'disabled')
    } catch {
      // Le serveur n'a pas répondu : on reste inactif plutôt que bloquant.
      setStatus('disabled')
    }
  }, [activeOrganizationId])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const enable = useCallback(async () => {
    if (activeOrganizationId === null) return
    setBusy(true)
    setError(null)
    try {
      const permission = await Notification.requestPermission()
      if (permission !== 'granted') {
        setStatus('denied')
        return
      }
      const key = await fetchPushPublicKey(activeOrganizationId)
      if (key === null) {
        setStatus('unavailable')
        return
      }
      const subscription = await subscribeToPush(key)
      await postSubscription(activeOrganizationId, subscription)
      setStatus('enabled')
    } catch {
      setError(t('push.error'))
    } finally {
      setBusy(false)
    }
  }, [activeOrganizationId, t])

  const disable = useCallback(async () => {
    if (activeOrganizationId === null) return
    setBusy(true)
    setError(null)
    try {
      const endpoint = await unsubscribeFromPush()
      if (endpoint !== null) {
        await deleteSubscription(activeOrganizationId, endpoint)
      }
      setStatus('disabled')
    } catch {
      setError(t('push.error'))
    } finally {
      setBusy(false)
    }
  }, [activeOrganizationId, t])

  return { status, busy, error, enable, disable }
}
