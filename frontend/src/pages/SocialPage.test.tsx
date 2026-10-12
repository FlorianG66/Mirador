// Tests de la page Réseaux sociaux (sous-phase 5c) : panneau complet, module
// non connecté (404 sur toutes les séries) et panne réseau. Même approche que
// WebPage.test.tsx : routeur mémoire + stub fetches globaux + QueryClient sans
// retry.
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it } from 'vitest'
import { routes } from '../app/routes.tsx'
import type { MetricPoint } from '../api/types.ts'
import { SOCIAL_METRIC_KEYS } from '../metrics/social.ts'
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

/** Gabarits des neuf séries du panneau social. */
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
  return SOCIAL_METRIC_KEYS.map((key) => ({
    match: new RegExp(`metrics\\/${escapeKey(key)}$`),
    respond: () => {
      if (mode === 'error' && key === 'social.impressions') {
        throw new Error('panne réseau simulée')
      }
      return json(seriesJson(key, pointsFor(key)))
    },
  }))
}

/** Données de démonstration fictives pour chaque clé (jamais de vraie marque). */
function pointsFor(key: string): MetricPoint[] {
  switch (key) {
    case 'social.followers':
      return dailyPoints([18_000, 18_400, 18_750, 19_100, 19_500], {
        items: [
          { name: 'linkedin', value: 8_400 },
          { name: 'instagram', value: 6_100 },
          { name: 'facebook', value: 3_200 },
          { name: 'x', value: 1_100 },
          { name: 'youtube', value: 700 },
        ],
      })
    case 'social.followers_growth':
      return dailyPoints([380, 400, 350, 360, 390])
    case 'social.impressions':
      return dailyPoints([6_400, 6_900, 6_700, 7_100, 7_400])
    case 'social.reach':
      return dailyPoints([4_200, 4_600, 4_500, 4_800, 5_050])
    case 'social.engagements':
      return dailyPoints([210, 240, 225, 260, 285])
    case 'social.engagement_rate':
      return dailyPoints([3.3, 3.5, 3.4, 3.7, 3.9])
    case 'social.mentions':
      return dailyPoints([46, 52, 44, 58, 61])
    case 'social.posts':
      return dailyPoints([2, 1, 2, 1, 2])
    case 'social.top_posts':
      return dailyPoints([210, 240, 225, 260, 285], {
        items: [
          { name: 'Coulisses de notre atelier', value: 92 },
          { name: '3 astuces pour gagner du temps', value: 74 },
          { name: 'Rencontre avec l’équipe support', value: 55 },
          { name: 'Nouveauté : notre offre d’automne', value: 38 },
        ],
      })
    default:
      return []
  }
}

// Session admin simulée, comme dans App.test.tsx, plus les neuf séries sociales.
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
      respond: () => json({ role: 'admin', modules: { social: 'view' } }),
    },
    ...panelRoutes(mode),
  ])
}

function renderSocial(mode: 'ok' | 'missing' | 'error' = 'ok') {
  stubEnvironment(mode)
  const router = createMemoryRouter(routes, { initialEntries: ['/social'] })
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('SocialPage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('affiche les quatre KPI, les graphiques et les classements', async () => {
    renderSocial('ok')

    expect(await screen.findByRole('heading', { name: 'Impressions vs portée' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Abonnés par réseau' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Croissance des abonnés' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: "Taux d'engagement" })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Mentions' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Meilleurs posts' })).toBeInTheDocument()

    // Classements (dimensions `items`), tous fictifs et traduits ou signalés.
    expect(screen.getByText('LinkedIn')).toBeInTheDocument()
    expect(screen.getByText('Instagram')).toBeInTheDocument()
    expect(screen.getByText('Coulisses de notre atelier')).toBeInTheDocument()

    // Mention obligatoire des données fictives (dépôt public, spec RGPD).
    expect(screen.getByText('Données de démonstration fictives')).toBeInTheDocument()
  })

  it('affiche l’état vide quand aucune série n’existe pour le module', async () => {
    renderSocial('missing')
    expect(await screen.findByText('Module réseaux sociaux pas encore connecté')).toBeInTheDocument()
  })

  it('affiche l’erreur et un bouton réessayer en cas de panne', async () => {
    renderSocial('error')
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('Impossible de charger les données')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Réessayer' })).toBeInTheDocument()
  })
})
