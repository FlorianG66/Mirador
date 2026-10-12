// Tests de la page Finance (sous-phase 5a) : panneau complet, module non
// connecté (404 sur toutes les séries) et panne réseau. Même approche que
// App.test.tsx : routeur mémoire + stub fetches globaux + QueryClient sans retry.
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it } from 'vitest'
import { routes } from '../app/routes.tsx'
import type { MetricPoint } from '../api/types.ts'
import { FINANCE_METRIC_KEYS } from '../metrics/finance.ts'
import { json, problem, stubFetch, type FetchRoute } from '../test/mockFetch.ts'

const DAY = 86_400_000
const BASE = Date.parse('2026-10-06T00:00:00Z')

/** Série JSON telle que renvoyée par l'API (MetricSeries). */
function seriesJson(
  key: string,
  points: MetricPoint[],
): { key: string; unit: string; period: string; points: MetricPoint[] } {
  return { key, unit: 'eur', period: 'P1D', points }
}

/** Points horodatés quotidiens à partir de valeurs simples. */
function dailyPoints(values: number[], lastDimensions?: Record<string, unknown>): MetricPoint[] {
  const withoutLast = values.slice(0, -1).map((value, index) => ({
    at: new Date(BASE + index * DAY).toISOString(),
    value,
  }))
  const last = {
    at: new Date(BASE + (values.length - 1) * DAY).toISOString(),
    value: values[values.length - 1] ?? 0,
  }
  return [
    ...withoutLast,
    lastDimensions === undefined ? last : { ...last, dimensions: lastDimensions },
  ]
}

/** Gabarits des huit séries du panneau financier. */
function panelRoutes(mode: 'ok' | 'missing' | 'error'): FetchRoute[] {
  if (mode === 'missing') {
    return [
      {
        match: /metrics\/[^/]+$/,
        respond: () => problem(404, 'Série inconnue pour cette organisation'),
      },
    ]
  }
  const escapeKey = (key: string) => key.replace(/\./g, '\\.')
  return FINANCE_METRIC_KEYS.map((key) => ({
    match: new RegExp(`metrics\\/${escapeKey(key)}$`),
    respond: () => {
      if (mode === 'error' && key === 'finance.revenue') {
        throw new Error('panne réseau simulée')
      }
      return json(seriesJson(key, pointsFor(key)))
    },
  }))
}

/** Données de démonstration fictives pour chaque clé (jamais de vraie entreprise). */
function pointsFor(key: string): MetricPoint[] {
  switch (key) {
    case 'finance.revenue':
      return dailyPoints([9_000, 9_700, 10_100, 10_800, 12_000])
    case 'finance.expenses':
      return dailyPoints([5_200, 5_600, 5_400, 5_900, 6_100])
    case 'finance.margin':
      return dailyPoints([3_800, 4_100, 4_700, 4_900, 5_900])
    case 'finance.cash':
      return dailyPoints([22_100, 26_200, 30_900, 35_800, 41_700])
    case 'finance.budget':
      return dailyPoints([10_000, 10_000, 10_000, 10_000, 10_000])
    case 'finance.invoices_outstanding':
      return dailyPoints([7, 6, 8, 9, 7], {
        aging: [
          { days: 30, count: 4 },
          { days: 60, count: 2 },
          { days: 90, count: 1 },
        ],
      })
    case 'finance.top_clients':
      return dailyPoints([9_000, 9_700, 10_100, 10_800, 12_000], {
        top: [
          { name: 'Client Alpha', amount: 42_000 },
          { name: 'Client Bravo', amount: 31_000 },
          { name: 'Client Charlie', amount: 22_000 },
        ],
      })
    case 'finance.top_suppliers':
      return dailyPoints([5_200, 5_600, 5_400, 5_900, 6_100], {
        top: [
          { name: 'Fournisseur Alpha', amount: 8_500 },
          { name: 'Fournisseur Bravo', amount: 6_400 },
        ],
      })
    default:
      return []
  }
}

// Session admin simulée, comme dans App.test.tsx, plus les huit séries.
function stubEnvironment(mode: 'ok' | 'missing' | 'error') {
  stubFetch([
    {
      match: /auth\/me$/,
      respond: () =>
        json({
          id: 'u1',
          email: 'admin@exemple.fr',
          memberships: [{ organization_id: 'org1', role: 'admin' }],
        }),
    },
    {
      match: /permissions$/,
      respond: () => json({ role: 'admin', modules: { finance: 'edit' } }),
    },
    ...panelRoutes(mode),
  ])
}

function renderFinance(mode: 'ok' | 'missing' | 'error' = 'ok') {
  stubEnvironment(mode)
  const router = createMemoryRouter(routes, { initialEntries: ['/finance'] })
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('FinancePage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('affiche les quatre KPI, les graphiques et les classements', async () => {
    renderFinance('ok')

    expect(await screen.findByText('Chiffre d\'affaires')).toBeInTheDocument()
    expect(screen.getByText('Trésorerie')).toBeInTheDocument()
    // « Marge » sert aussi de titre de graphique : getAllByText reste robuste.
    expect(screen.getAllByText('Marge').length).toBeGreaterThan(0)
    expect(screen.getByText('Impayés')).toBeInTheDocument()

    expect(
      screen.getByRole('heading', { name: "Chiffre d'affaires vs dépenses" }),
    ).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Ancienneté des impayés' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Top clients' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Top fournisseurs' })).toBeInTheDocument()

    // Tops (dimensions des fichiers de données), tous fictifs.
    expect(screen.getByText('Client Alpha')).toBeInTheDocument()
    expect(screen.getByText('Fournisseur Alpha')).toBeInTheDocument()
    // Tranches d'ancienneté.
    expect(screen.getByText('0-30 j')).toBeInTheDocument()
    expect(screen.getByText('60 j et plus')).toBeInTheDocument()
    // Mention obligatoire des données fictives (dépôt public, spec RGPD).
    expect(screen.getByText('Données de démonstration fictives')).toBeInTheDocument()
  })

  it('affiche l’état vide quand aucune série n’existe pour le module', async () => {
    renderFinance('missing')
    expect(
      await screen.findByText('Module financier pas encore connecté'),
    ).toBeInTheDocument()
  })

  it('affiche l’erreur et un bouton réessayer en cas de panne', async () => {
    renderFinance('error')
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('Impossible de charger les données')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Réessayer' })).toBeInTheDocument()
  })
})
