// Enregistrement du service worker Web Push (sous-phase 6c-iii-b) et des
// opérations d'abonnement du navigateur. Aucun secret ici : la clé VAPID
// *publique* vient de l'API, la clé privée ne quitte jamais le serveur.
//
// Le service worker n'existe qu'en production : en développement, Vite sert les
// modules à la volée et un SW en cache masquerait les changements. On ne
// l'enregistre donc que lorsque l'application tourne sur un serveur de
// production (`import.meta.env.PROD`).

/** Un abonnement tel que le navigateur le produit (`PushSubscription.toJSON()`). */
export interface BrowserSubscription {
  endpoint: string
  keys: { p256dh: string; auth: string }
}

/** Vrai si le navigateur sait faire du Web Push (Service Worker + PushManager). */
export function supportsPush(): boolean {
  if (typeof window === 'undefined') return false
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return false
  return 'Notification' in window
}

/**
 * Enregistre le service worker de l'application (une seule fois, en production).
 * Renvoie `null` en développement ou quand l'API n'est pas disponible : l'appel
 * reste sans effet plutôt que de lever, la fonctionnalité étant optionnelle.
 */
export async function registerServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (!import.meta.env.PROD) return null
  if (!supportsPush()) return null
  try {
    return await navigator.serviceWorker.register('/sw.js', { scope: '/' })
  } catch {
    // Un échec d'enregistrement ne doit pas empêcher l'application de démarrer.
    return null
  }
}

/** Convertit une clé VAPID base64url en `Uint8Array` (format attendu par l'API). */
export function urlBase64ToUint8Array(base64Url: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64Url.length % 4)) % 4)
  const base64 = (base64Url + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  const bytes = new Uint8Array(new ArrayBuffer(raw.length))
  for (let index = 0; index < raw.length; index += 1) {
    bytes[index] = raw.charCodeAt(index)
  }
  return bytes
}

/** Abonnement actif du navigateur, ou `null` si aucun (ou pas de support). */
export async function getSubscription(): Promise<PushSubscription | null> {
  if (!supportsPush()) return null
  const registration = await navigator.serviceWorker.ready
  return registration.pushManager.getSubscription()
}

/**
 * Abonne le navigateur au service de push avec la clé VAPID publique fournie.
 * `userVisibleOnly` est obligatoire : un push doit toujours être visible.
 */
export async function subscribeToPush(publicKey: string): Promise<BrowserSubscription> {
  const registration = await navigator.serviceWorker.ready
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(publicKey),
  })
  const json = subscription.toJSON()
  return {
    endpoint: subscription.endpoint,
    keys: { p256dh: json.keys?.p256dh ?? '', auth: json.keys?.auth ?? '' },
  }
}

/** Désabonne le navigateur et renvoie l'endpoint retiré (ou `null` si aucun). */
export async function unsubscribeFromPush(): Promise<string | null> {
  const subscription = await getSubscription()
  if (subscription === null) return null
  const endpoint = subscription.endpoint
  await subscription.unsubscribe()
  return endpoint
}

/** Révoque l'enregistrement du service worker (désinstallation complète). */
export async function unregisterServiceWorker(): Promise<void> {
  if (!supportsPush()) return
  const registration = await navigator.serviceWorker.getRegistration('/')
  await registration?.unregister()
}
