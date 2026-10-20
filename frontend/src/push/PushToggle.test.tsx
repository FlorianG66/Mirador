// Tests du réglage des notifications Web Push (sous-phase 6c-iii-b) : état
// initial (désactivé), activation (permission accordée → abonnement envoyé au
// serveur), refus de permission, désactivation, et cas navigateur non supporté.
// L'i18n (FR) est initialisée par le setup partagé ; les primitives du navigateur
// et les appels API sont simulés (aucune donnée réelle, aucune vraie clé).
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AuthContext, type AuthContextValue } from '../auth/context.ts'
import { json, stubFetch, type FetchRoute } from '../test/mockFetch.ts'
import { PushToggle } from './PushToggle.tsx'

const ENDPOINT = 'https://push.example.test/v1/abc'

/** Faux abonnement de navigateur, au format de `PushSubscription.toJSON()`. */
function fakeSubscription() {
  return {
    endpoint: ENDPOINT,
    unsubscribe: vi.fn(async () => true),
    toJSON: () => ({ endpoint: ENDPOINT, keys: { p256dh: 'BKey', auth: 'Secret' } }),
  }
}

/** Installe les primitives Web Push du navigateur, avec un abonnement initial. */
function installBrowser(
  options: { existing?: ReturnType<typeof fakeSubscription> | null; permission?: string } = {},
) {
  const subscription = options.existing ?? null
  const pushManager = {
    getSubscription: vi.fn(async () => subscription),
    subscribe: vi.fn(async () => fakeSubscription()),
  }
  const registration = { pushManager }
  vi.stubGlobal('navigator', {
    serviceWorker: {
      ready: Promise.resolve(registration),
      getRegistration: vi.fn(async () => registration),
    },
  })
  vi.stubGlobal('PushManager', class {})
  vi.stubGlobal('Notification', {
    permission: options.permission ?? 'default',
    requestPermission: vi.fn(async () => options.permission ?? 'granted'),
  })
  return { pushManager }
}

function pushRoutes(state: { posted: number; deleted: number }): FetchRoute[] {
  return [
    {
      match: /push\/public-key$/,
      // Clé VAPID factice, en base64url valide (comme le vrai envoi du serveur).
      respond: () =>
        json({
          public_key:
            'Y2xlLXZhcGlkLXB1YmxpcXVlLWZhY3RpY2UtZGUtdGVzdC1wb3VyLWpzZG9tLTAxMjM0NTY3ODlhYmNkZWY',
        }),
    },
    {
      match: /push\/subscriptions$/,
      respond: (request) => {
        if (request.method === 'DELETE') {
          state.deleted += 1
          return new Response(null, { status: 204 })
        }
        state.posted += 1
        return json(
          { id: 'sub1', endpoint: ENDPOINT, user_agent: null, created_at: '2026-10-20T08:00:00Z' },
          201,
        )
      },
    },
  ]
}

function authValue(): AuthContextValue {
  return {
    status: 'authenticated',
    user: null,
    activeOrganizationId: 'org1',
    permissions: null,
    reload: async () => undefined,
  }
}

function renderToggle() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <AuthContext.Provider value={authValue()}>
      <QueryClientProvider client={queryClient}>
        <PushToggle />
      </QueryClientProvider>
    </AuthContext.Provider>,
  )
}

describe('PushToggle', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('affiche l’état désactivé et propose d’activer quand le navigateur est compatible', async () => {
    installBrowser()
    stubFetch(pushRoutes({ posted: 0, deleted: 0 }))

    renderToggle()

    expect(
      await screen.findByText('Les notifications ne sont pas encore activées sur cet appareil.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Activer les notifications/ })).toBeEnabled()
  })

  it('active les notifications : permission accordée puis abonnement envoyé au serveur', async () => {
    const { pushManager } = installBrowser({ permission: 'granted' })
    const state = { posted: 0, deleted: 0 }
    stubFetch(pushRoutes(state))

    renderToggle()
    const button = await screen.findByRole('button', { name: /Activer les notifications/ })
    button.click()

    await waitFor(() => expect(state.posted).toBe(1))
    expect(pushManager.subscribe).toHaveBeenCalledOnce()
    expect(
      await screen.findByText('Les notifications sont activées sur cet appareil.'),
    ).toBeInTheDocument()
  })

  it('n’abonne rien si la permission est refusée', async () => {
    installBrowser({ permission: 'denied' })
    const state = { posted: 0, deleted: 0 }
    stubFetch(pushRoutes(state))

    renderToggle()

    expect(
      await screen.findByText(/Vous avez refusé les notifications dans votre navigateur/),
    ).toBeInTheDocument()
    expect(state.posted).toBe(0)
    expect(screen.queryByRole('button', { name: /Activer les notifications/ })).toBeNull()
  })

  it('désactive les notifications : désabonnement navigateur puis suppression serveur', async () => {
    installBrowser({ existing: fakeSubscription(), permission: 'granted' })
    const state = { posted: 0, deleted: 0 }
    stubFetch(pushRoutes(state))

    renderToggle()
    const button = await screen.findByRole('button', { name: /Désactiver/ })
    button.click()

    await waitFor(() => expect(state.deleted).toBe(1))
    expect(
      await screen.findByText('Les notifications ne sont pas encore activées sur cet appareil.'),
    ).toBeInTheDocument()
  })

  it('n’affiche rien quand le navigateur ne prend pas en charge les notifications', async () => {
    // Ni `serviceWorker` ni `PushManager` : la fonctionnalité est indisponible.
    vi.stubGlobal('navigator', {})
    vi.stubGlobal('Notification', { permission: 'default' })
    stubFetch(pushRoutes({ posted: 0, deleted: 0 }))

    renderToggle()

    await waitFor(() =>
      expect(
        screen.getByText('Ce navigateur ne prend pas en charge les notifications hors onglet.'),
      ).toBeInTheDocument(),
    )
    expect(screen.queryByRole('button', { name: /Activer les notifications/ })).toBeNull()
  })
})
