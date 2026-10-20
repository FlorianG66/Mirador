// Tests du centre de notifications (sous-phase 6c-ii) : compteur de non-lus,
// ouverture du panneau, traduction des notifications (titre + corps formaté),
// marquage lu / tout lu, état vide, fermeture par Échap et navigation vers le
// module concerné. L'i18n (FR) est initialisée par le setup partagé ; les appels
// API sont simulés (aucune donnée réelle, AGENTS.md §5).
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { describe, expect, it } from 'vitest'
import { AuthContext, type AuthContextValue } from '../auth/context.ts'
import { json, stubFetch, type FetchRoute } from '../test/mockFetch.ts'
import { NotificationBell } from './NotificationBell.tsx'

const NOW = '2026-10-19T08:00:00Z'

interface NotificationStub {
  id: string
  kind: string
  params: Record<string, unknown>
  link: string | null
  read_at: string | null
  created_at: string
}

function goalAchieved(overrides: Partial<NotificationStub> = {}): NotificationStub {
  return {
    id: 'n1',
    kind: 'goal.achieved',
    params: {
      metric_key: 'finance.revenue',
      target_value: 100000,
      period_days: 30,
      direction: 'at_least',
    },
    link: '/finance',
    read_at: null,
    created_at: NOW,
    ...overrides,
  }
}

/** Sink de test : la liste renvoyée évolue avec les écritures simulées. */
interface BellState {
  items: NotificationStub[]
  unread: number
  readCalls: number
  readAllCalls: number
}

function bellRoutes(state: BellState): FetchRoute[] {
  return [
    {
      match: /organizations\/[^/]+\/notifications\/read-all$/,
      respond: () => {
        state.readAllCalls += 1
        state.unread = 0
        state.items = state.items.map((item) => ({ ...item, read_at: NOW }))
        return new Response(null, { status: 204 })
      },
    },
    {
      match: /organizations\/[^/]+\/notifications\/[^/]+\/read$/,
      respond: () => {
        state.readCalls += 1
        state.unread = Math.max(0, state.unread - 1)
        return new Response(null, { status: 204 })
      },
    },
    {
      match: /organizations\/[^/]+\/notifications$/,
      respond: () => json({ items: state.items, unread_count: state.unread }),
    },
  ]
}

function authValue(organizationId: string | null): AuthContextValue {
  return {
    status: 'authenticated',
    user: null,
    activeOrganizationId: organizationId,
    permissions: null,
    reload: async () => undefined,
  }
}

function renderBell(organizationId: string | null = 'org1') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const router = createMemoryRouter(
    [
      {
        path: '/',
        element: (
          <AuthContext.Provider value={authValue(organizationId)}>
            <QueryClientProvider client={queryClient}>
              <NotificationBell />
            </QueryClientProvider>
          </AuthContext.Provider>
        ),
      },
      { path: '/finance', element: <div data-testid="finance-page" /> },
    ],
    { initialEntries: ['/'] },
  )
  return { router, queryClient, ...render(<RouterProvider router={router} />) }
}

async function openPanel() {
  fireEvent.click(await screen.findByRole('button', { name: /Notifications/ }))
  return screen.findByRole('dialog', { name: 'Notifications' })
}

describe('NotificationBell', () => {
  it('affiche le compteur de non-lus et traduit les notifications', async () => {
    const state: BellState = { items: [goalAchieved()], unread: 1, readCalls: 0, readAllCalls: 0 }
    stubFetch(bellRoutes(state))

    renderBell()

    expect(await screen.findByTestId('notifications-badge')).toHaveTextContent('1')

    await openPanel()

    expect(screen.getByText('Objectif atteint')).toBeInTheDocument()
    const body = screen.getByText(/a atteint sa cible/)
    expect(body).toHaveTextContent("Chiffre d'affaires")
    expect(body.textContent).toContain('100')
  })

  it('marque tout comme lu et masque le compteur', async () => {
    const state: BellState = { items: [goalAchieved()], unread: 1, readCalls: 0, readAllCalls: 0 }
    stubFetch(bellRoutes(state))

    renderBell()
    // Attend que le compteur soit chargé avant d'ouvrir (sinon le bouton est
    // encore désactivé, faute de non-lus connus).
    await screen.findByTestId('notifications-badge')
    await openPanel()

    fireEvent.click(screen.getByRole('button', { name: 'Tout marquer comme lu' }))

    await waitFor(() => expect(state.readAllCalls).toBe(1))
    await waitFor(() =>
      expect(screen.queryByTestId('notifications-badge')).not.toBeInTheDocument(),
    )
  })

  it('navigue vers le module et marque la notification lue', async () => {
    const state: BellState = { items: [goalAchieved()], unread: 1, readCalls: 0, readAllCalls: 0 }
    stubFetch(bellRoutes(state))

    renderBell()
    await openPanel()

    fireEvent.click(await screen.findByRole('link', { name: /Objectif atteint/ }))

    expect(await screen.findByTestId('finance-page')).toBeInTheDocument()
    await waitFor(() => expect(state.readCalls).toBe(1))
  })

  it('affiche un état vide quand il n’y a aucune notification', async () => {
    const state: BellState = { items: [], unread: 0, readCalls: 0, readAllCalls: 0 }
    stubFetch(bellRoutes(state))

    renderBell()
    await openPanel()

    expect(await screen.findByText('Aucune notification')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Tout marquer comme lu' }),
    ).toBeDisabled()
  })

  it('se ferme avec la touche Échap', async () => {
    const state: BellState = { items: [goalAchieved()], unread: 1, readCalls: 0, readAllCalls: 0 }
    stubFetch(bellRoutes(state))

    renderBell()
    await openPanel()

    fireEvent.keyDown(window, { key: 'Escape' })

    await waitFor(() =>
      expect(screen.queryByRole('dialog', { name: 'Notifications' })).not.toBeInTheDocument(),
    )
  })
})
