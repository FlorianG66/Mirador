// Tests de la page Web analytics (sous-phase 5b) : panneau complet, module non
// connecté (404 sur toutes les séries) et panne réseau. Même approche que
// FinancePage.test.tsx : routeur mémoire + stub fetches globaux + QueryClient
// sans retry.
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it } from 'vitest'
import { routes } from '../app/routes.tsx'
import type { MetricPoint } from '../api/types.ts'
import { WEB_METRIC_KEYS } from '../metrics/web.ts'
import { json, problem, stubFetch, type FetchRoute } from '../test/mockFetch.ts'

const DAY = 86_400_000
const BASE = Date.parse('2026-10-06T00:00:00Z')

/** Série JSON telle que renvoyée par l'API (MetricSeries). */
function seriesJson(
  key: string,
  points: MetricPoint[],
): { key: string; unit: string; period: string; points: MetricPoint[] } {
  return { key, unit: 'count', period: 'P1D', points }
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

/** Gabarits des dix séries du panneau web. */
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
  return WEB_METRIC_KEYS.map((key) => ({
    match: new RegExp(`metrics\\/${escapeKey(key)}$`),
    respond: () => {
      if (mode === 'error' && key === 'web.sessions') {
        throw new Error('panne réseau simulée')
      }
      return json(seriesJson(key, pointsFor(key)))
    },
  }))
}

/** Données de démonstration fictives pour chaque clé (jamais de vraie entreprise). */
function pointsFor(key: string): MetricPoint[] {
  switch (key) {
    case 'web.sessions':
      return dailyPoints([1_400, 1_520, 1_480, 1_610, 1_730])
    case 'web.visitors':
      return dailyPoints([1_050, 1_140, 1_100, 1_205, 1_300])
    case 'web.pageviews':
      return dailyPoints([3_200, 3_500, 3_410, 3_720, 4_000])
    case 'web.engagement_rate':
      return dailyPoints([52, 55, 54, 58, 61])
    case 'web.avg_session_duration':
      return dailyPoints([118, 124, 121, 133, 142])
    case 'web.conversions':
      return dailyPoints([28, 31, 30, 35, 39])
    case 'web.traffic_sources':
      return dailyPoints([1_400, 1_520, 1_480, 1_610, 1_730], {
        items: [
          { name: 'organic_search', value: 720 },
          { name: 'direct', value: 430 },
          { name: 'social', value: 310 },
          { name: 'referral', value: 180 },
          { name: 'email', value: 90 },
        ],
      })
    case 'web.top_pages':
      return dailyPoints([3_200, 3_500, 3_410, 3_720, 4_000], {
        items: [
          { name: '/', value: 1_200 },
          { name: '/pricing', value: 520 },
          { name: '/blog/guide', value: 380 },
        ],
      })
    case 'web.devices':
      return dailyPoints([1_050, 1_140, 1_100, 1_205, 1_300], {
        items: [
          { name: 'desktop', value: 640 },
          { name: 'mobile', value: 520 },
          { name: 'tablet', value: 140 },
        ],
      })
    case 'web.countries':
      return dailyPoints([1_050, 1_140, 1_100, 1_205, 1_300], {
        items: [
          { name: 'FR', value: 700 },
          { name: 'BE', value: 240 },
          { name: 'CH', value: 150 },
        ],
      })
    default:
      return []
  }
}

// Session admin simulée, comme dans App.test.tsx, plus les dix séries web.
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
      respond: () => json({ role: 'admin', modules: { web: 'view' } }),
    },
    ...panelRoutes(mode),
  ])
}

function renderWeb(mode: 'ok' | 'missing' | 'error' = 'ok') {
  stubEnvironment(mode)
  const router = createMemoryRouter(routes, { initialEntries: ['/web'] })
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('WebPage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('affiche les quatre KPI, les graphiques et les répartitions', async () => {
    renderWeb('ok')

    expect(await screen.findByRole('heading', { name: 'Sessions vs visiteurs' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Sources de trafic' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Pages les plus vues' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Appareils' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Pays' })).toBeInTheDocument()

    // Répartitions (dimensions `items`), toutes fictives et traduites.
    expect(screen.getByText('Recherche organique')).toBeInTheDocument()
    expect(screen.getByText('Accès direct')).toBeInTheDocument()
    expect(screen.getByText('/pricing')).toBeInTheDocument()
    expect(screen.getByText('Ordinateur')).toBeInTheDocument()
    expect(screen.getByText('Mobile')).toBeInTheDocument()
    expect(screen.getByText('France')).toBeInTheDocument()
    expect(screen.getByText('Belgique')).toBeInTheDocument()

    // Mention obligatoire des données fictives (dépôt public, spec RGPD).
    expect(screen.getByText('Données de démonstration fictives')).toBeInTheDocument()
  })

  it('affiche l’état vide quand aucune série n’existe pour le module', async () => {
    renderWeb('missing')
    expect(await screen.findByText('Module web pas encore connecté')).toBeInTheDocument()
  })

  it('affiche l’erreur et un bouton réessayer en cas de panne', async () => {
    renderWeb('error')
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('Impossible de charger les données')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Réessayer' })).toBeInTheDocument()
  })
})
