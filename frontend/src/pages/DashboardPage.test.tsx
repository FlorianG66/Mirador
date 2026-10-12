// Tests de la page « Vue d'ensemble » (sous-phase 5f) : KPI clés, santé
// d'exploitation, fil d'activité (admin) et états vide/erreur. Même approche
// que les autres pages : routeur mémoire + stub fetches + QueryClient sans retry.
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it } from 'vitest'
import { routes } from '../app/routes.tsx'
import { json, problem, stubFetch, type FetchRoute } from '../test/mockFetch.ts'

const NOW = '2026-10-12T09:00:00Z'

interface PulseBody {
  kpis: unknown[]
  health: { status: string; modules_with_data: number; modules_total: number }
  activity: unknown[]
}

function kpi(module: string, metricKey: string, unit: string, value: number): unknown {
  return {
    module,
    metric_key: metricKey,
    unit,
    value,
    previous_value: value - 1,
    captured_at: NOW,
  }
}

// Session simulée : rôle admin par défaut, surchargeable pour tester un membre.
function stubEnvironment(pulse: PulseBody | 'error', role: 'admin' | 'member' = 'admin') {
  const audit: FetchRoute[] = [
    {
      match: /auth\/me$/,
      respond: () =>
        json({
          id: 'u1',
          email: 'admin@exemple.fr',
          memberships: [{ organization_id: 'org1', role }],
        }),
    },
    {
      match: /permissions$/,
      respond: () => json({ role, modules: { finance: 'view' } }),
    },
    {
      match: /organizations\/[^/]+\/pulse$/,
      respond: () =>
        pulse === 'error' ? problem(500, 'Panne simulée') : json(pulse),
    },
  ]
  stubFetch(audit)
}

function renderDashboard() {
  const router = createMemoryRouter(routes, { initialEntries: ['/'] })
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('DashboardPage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('affiche les KPI, la santé et le fil d’activité pour un admin', async () => {
    stubEnvironment({
      kpis: [
        kpi('finance', 'finance.revenue', 'EUR', 42_100),
        kpi('finance', 'finance.margin', 'EUR', 12_000),
        kpi('web', 'web.visitors', 'visitors', 3_200),
      ],
      health: { status: 'good', modules_with_data: 2, modules_total: 2 },
      activity: [
        {
          id: 'a1',
          action: 'invitation.created',
          actor_user_id: null,
          resource_type: null,
          resource_id: null,
          payload: null,
          created_at: NOW,
        },
      ],
    })
    renderDashboard()

    expect(await screen.findByText("Chiffre d'affaires")).toBeInTheDocument()
    expect(screen.getByText('Marge')).toBeInTheDocument()
    expect(screen.getByText('Visiteurs')).toBeInTheDocument()
    expect(screen.getByText('Tous les modules sont alimentés')).toBeInTheDocument()
    expect(screen.getByText('Invitation envoyée')).toBeInTheDocument()
  })

  it('réserve le fil d’activité aux administrateurs', async () => {
    stubEnvironment(
      {
        kpis: [kpi('finance', 'finance.revenue', 'EUR', 1_000)],
        health: { status: 'good', modules_with_data: 1, modules_total: 1 },
        activity: [],
      },
      'member',
    )
    renderDashboard()

    expect(await screen.findByText('Réservée aux administrateurs')).toBeInTheDocument()
  })

  it('affiche l’état vide et la santé en alerte sans donnée', async () => {
    stubEnvironment({
      kpis: [],
      health: { status: 'warning', modules_with_data: 0, modules_total: 4 },
      activity: [],
    })
    renderDashboard()

    expect(await screen.findByText('Pas encore de données à synthétiser')).toBeInTheDocument()
    expect(screen.getByText('0/4 modules alimentés')).toBeInTheDocument()
  })

  it('affiche l’erreur et un bouton réessayer en cas de panne', async () => {
    stubEnvironment('error')
    renderDashboard()

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Réessayer' })).toBeInTheDocument()
  })
})
