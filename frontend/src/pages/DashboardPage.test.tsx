// Tests de la page « Vue d'ensemble » (sous-phase 5f) : KPI clés, santé
// d'exploitation, fil d'activité (admin) et états vide/erreur. La comparaison de
// périodes (phase 6a) est couverte par un test dédié. Même approche que les
// autres pages : routeur mémoire + stub fetches + QueryClient sans retry.
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { routes } from '../app/routes.tsx'
import { json, problem, stubFetch, type FetchRoute } from '../test/mockFetch.ts'

const NOW = '2026-10-12T09:00:00Z'

interface PulseBody {
  kpis: unknown[]
  health: { status: string; modules_with_data: number; modules_total: number }
  activity: unknown[]
}

/** Comparaison simulée d'un KPI : valeur de la fenêtre et de la précédente. */
interface ComparisonEntry {
  current: number
  previous: number
}

/** Corps envoyé à la création d'un objectif (schéma GoalCreate). */
interface GoalCreateBody {
  metric_key: string
  label?: string | null
  direction: string
  target_value: number
  period_days: number
}

/** Objectif lu (GoalOut) : définition + progression calculée. */
function goalBody(overrides: Record<string, unknown> = {}): unknown {
  return {
    id: 'goal-1',
    metric_key: 'finance.revenue',
    label: 'Objectif CA',
    direction: 'at_least',
    target_value: 100000,
    period_days: 30,
    progress: {
      status: 'on_track',
      current_value: 60000,
      previous_value: 50000,
      progress_percent: 60,
      unit: 'EUR',
    },
    created_at: NOW,
    updated_at: NOW,
    ...overrides,
  }
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

// Réponse de l'endpoint de comparaison, au format du schéma OpenAPI.
function comparisonBody(
  metricKey: string,
  { current, previous }: { current: number; previous: number },
  days: number,
): unknown {
  const change = current - previous
  return {
    key: metricKey,
    unit: 'EUR',
    period: 'P1D',
    aggregation: 'sum',
    days,
    current: [{ at: NOW, value: current, dimensions: {} }],
    previous: [{ at: NOW, value: previous, dimensions: {} }],
    summary: {
      current_value: current,
      previous_value: previous,
      change,
      change_percent: previous === 0 ? null : (change / Math.abs(previous)) * 100,
    },
  }
}

// Session simulée : rôle admin par défaut, surchargeable pour tester un membre.
// `comparisons` : clé métrique → écart simulé ; une clé absente répond 404, ce qui
// fait retomber la carte sur la dernière valeur du Pouls. `goals` : objectifs
// renvoyés par le panneau ; un POST les ajoute et appelle `onGoalCreated`.
function stubEnvironment(
  pulse: PulseBody | 'error',
  role: 'admin' | 'member' = 'admin',
  comparisons: Record<string, ComparisonEntry> = {},
  goals: unknown[] = [],
  onGoalCreated?: (body: GoalCreateBody) => void,
) {
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
    {
      match: /metrics\/[^/]+\/comparison$/,
      respond: (request) => {
        const url = new URL(request.url)
        const metricKey = url.pathname.split('/').at(-2) ?? ''
        const entry = comparisons[metricKey]
        if (!entry) {
          return problem(404, 'Aucune donnée sur la période.')
        }
        const days = Number(url.searchParams.get('days') ?? 30)
        return json(comparisonBody(metricKey, entry, days))
      },
    },
    {
      match: /organizations\/[^/]+\/goals$/,
      respond: (request) => {
        if (request.method === 'POST') {
          return request.json().then((body: GoalCreateBody) => {
            onGoalCreated?.(body)
            const created = {
              ...body,
              id: `goal-${body.metric_key}`,
              progress: {
                status: 'unknown',
                current_value: null,
                previous_value: null,
                progress_percent: null,
                unit: null,
              },
              created_at: NOW,
              updated_at: NOW,
            }
            goals.push(created)
            return json(created, 201)
          })
        }
        return json(goals)
      },
    },
    {
      match: /organizations\/[^/]+\/goals\/[^/]+$/,
      respond: (request) => {
        const id = new URL(request.url).pathname.split('/').at(-1) ?? ''
        const index = goals.findIndex((goal) => (goal as { id?: string }).id === id)
        if (request.method === 'DELETE') {
          if (index >= 0) {
            goals.splice(index, 1)
          }
          return new Response(null, { status: 204 })
        }
        if (request.method === 'PATCH') {
          return request.json().then((body: Record<string, unknown>) => {
            if (index >= 0) {
              goals[index] = { ...(goals[index] as Record<string, unknown>), ...body }
            }
            return json(goals[index] ?? {})
          })
        }
        return json(goals[index] ?? {})
      },
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

  it('compare les KPI sur la période choisie', async () => {
    stubEnvironment(
      {
        kpis: [
          kpi('finance', 'finance.revenue', 'EUR', 42_100),
          kpi('finance', 'finance.margin', 'EUR', 12_000),
        ],
        health: { status: 'good', modules_with_data: 1, modules_total: 1 },
        activity: [],
      },
      'admin',
      {
        'finance.revenue': { current: 60_000, previous: 40_000 },
        'finance.margin': { current: 1_200, previous: 1_500 },
      },
    )
    renderDashboard()

    // L'écart vient de la fenêtre sélectionnée (≈ +50 % et -20 %), pas du point
    // précédent du Pouls.
    expect(await screen.findByText(/\+50/)).toBeInTheDocument()
    expect(screen.getByText(/-20/)).toBeInTheDocument()

    // 30 jours par défaut ; choisir 7 jours déplace l'option active.
    const thirty = screen.getByRole('button', { name: '30 j' })
    expect(thirty).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(screen.getByRole('button', { name: '7 j' }))
    expect(screen.getByRole('button', { name: '7 j' })).toHaveAttribute('aria-pressed', 'true')
    expect(thirty).toHaveAttribute('aria-pressed', 'false')
  })

  it('affiche les objectifs avec progression et statut', async () => {
    stubEnvironment(
      {
        kpis: [],
        health: { status: 'warning', modules_with_data: 0, modules_total: 1 },
        activity: [],
      },
      'admin',
      {},
      [goalBody()],
    )
    renderDashboard()

    expect(await screen.findByText('Objectif CA')).toBeInTheDocument()
    expect(screen.getByText('En bonne voie')).toBeInTheDocument()
    expect(screen.getByText('60 % de la cible')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Nouvel objectif' })).toBeInTheDocument()
  })

  it('crée un objectif et rafraîchit la liste', async () => {
    const created: GoalCreateBody[] = []
    stubEnvironment(
      {
        kpis: [],
        health: { status: 'warning', modules_with_data: 0, modules_total: 1 },
        activity: [],
      },
      'admin',
      {},
      [],
      (body) => created.push(body),
    )
    renderDashboard()

    fireEvent.click(await screen.findByRole('button', { name: 'Nouvel objectif' }))
    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '50000' } })
    const saveButton = screen.getByRole('button', { name: 'Enregistrer' })
    fireEvent.submit(saveButton.closest('form')!)

    // Le libellé est vide : l'affichage retombe sur le nom du KPI ciblé. On
    // réinterroge le DOM à chaque essai : l'invalidation remplace la ligne.
    await waitFor(() =>
      expect(screen.getByText("Chiffre d'affaires")).toBeInTheDocument(),
    )
    expect(created[0]).toMatchObject({
      metric_key: 'finance.revenue',
      direction: 'at_least',
      target_value: 50_000,
      period_days: 30,
    })
  })

  it('masque les actions d’écriture sans droit d’édition', async () => {
    stubEnvironment(
      {
        kpis: [],
        health: { status: 'warning', modules_with_data: 0, modules_total: 1 },
        activity: [],
      },
      'member',
      {},
      [goalBody()],
    )
    renderDashboard()

    expect(await screen.findByText('Objectif CA')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Nouvel objectif' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Modifier' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Supprimer' })).not.toBeInTheDocument()
  })

  it('modifie un objectif existant', async () => {
    const goals: unknown[] = [goalBody()]
    stubEnvironment(
      {
        kpis: [],
        health: { status: 'warning', modules_with_data: 0, modules_total: 1 },
        activity: [],
      },
      'admin',
      {},
      goals,
    )
    renderDashboard()

    fireEvent.click(await screen.findByRole('button', { name: 'Modifier' }))
    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '250000' } })
    fireEvent.submit(screen.getByRole('button', { name: 'Enregistrer' }).closest('form')!)

    await waitFor(() =>
      expect((goals[0] as { target_value?: number }).target_value).toBe(250_000),
    )
  })

  it('supprime un objectif après confirmation', async () => {
    vi.stubGlobal('confirm', () => true)
    const goals: unknown[] = [goalBody()]
    stubEnvironment(
      {
        kpis: [],
        health: { status: 'warning', modules_with_data: 0, modules_total: 1 },
        activity: [],
      },
      'admin',
      {},
      goals,
    )
    renderDashboard()

    fireEvent.click(await screen.findByRole('button', { name: 'Supprimer' }))

    await waitFor(() => expect(goals).toHaveLength(0))
    expect(await screen.findByText('Aucun objectif défini')).toBeInTheDocument()
  })
})
