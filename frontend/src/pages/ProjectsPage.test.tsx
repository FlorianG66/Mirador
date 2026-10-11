// Tests de la page Projets & tâches (sous-phase 5d) : panneau complet, module
// non connecté (404 sur toutes les séries) et panne réseau. Même approche que
// SocialPage.test.tsx : routeur mémoire + stub fetches globaux + QueryClient
// sans retry.
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it } from 'vitest'
import { routes } from '../app/routes.tsx'
import type { MetricPoint } from '../api/types.ts'
import { PROJECT_METRIC_KEYS } from '../metrics/projects.ts'
import { json, problem, stubFetch, type FetchRoute } from '../test/mockFetch.ts'

const DAY = 86_400_000
const BASE = Date.parse('2026-10-06T00:00:00Z')

/** Série JSON telle que renvoyée par l'API (MetricSeries). */
function seriesJson(
  key: string,
  points: MetricPoint[],
): { key: string; unit: string; period: string; points: MetricPoint[] } {
  return { key, unit: 'tasks', period: 'P1D', points }
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

/** Gabarits des dix séries du panneau projets. */
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
  return PROJECT_METRIC_KEYS.map((key) => ({
    match: new RegExp(`metrics\\/${escapeKey(key)}$`),
    respond: () => {
      if (mode === 'error' && key === 'projects.open_tasks') {
        throw new Error('panne réseau simulée')
      }
      return json(seriesJson(key, pointsFor(key)))
    },
  }))
}

/** Données de démonstration fictives pour chaque clé (jamais de salarié réel). */
function pointsFor(key: string): MetricPoint[] {
  switch (key) {
    case 'projects.tasks_done':
      return dailyPoints([16, 18, 15, 17, 19])
    case 'projects.tasks_created':
      return dailyPoints([18, 20, 17, 21, 22])
    case 'projects.open_tasks':
      return dailyPoints([80, 82, 84, 88, 91])
    case 'projects.overdue_tasks':
      return dailyPoints([6, 7, 6, 8, 9])
    case 'projects.avg_completion_time':
      return dailyPoints([6.2, 6.5, 6.4, 6.7, 6.6])
    case 'projects.avg_progress':
      return dailyPoints([52, 54, 55, 57, 58])
    case 'projects.active_projects':
      return dailyPoints([9, 9, 10, 10, 11])
    case 'projects.tasks_by_status':
      return dailyPoints([80, 82, 84, 88, 91], {
        items: [
          { name: 'todo', value: 30 },
          { name: 'in_progress', value: 28 },
          { name: 'review', value: 20 },
          { name: 'blocked', value: 13 },
        ],
      })
    case 'projects.person_load':
      return dailyPoints([80, 82, 84, 88, 91], {
        items: [
          { name: 'Camille Moreau', value: 24 },
          { name: 'Lucas Bernard', value: 20 },
          { name: 'Inès Robert', value: 18 },
          { name: 'Naomi Petit', value: 16 },
          { name: 'Hugo Dubois', value: 13 },
        ],
      })
    case 'projects.upcoming_milestones':
      return dailyPoints([28, 27, 26, 25, 24], {
        items: [
          { name: 'Recette finale', value: 3 },
          { name: 'Déploiement bêta', value: 5 },
          { name: 'Livraison du module M1', value: 7 },
          { name: 'Audit technique', value: 9 },
        ],
      })
    default:
      return []
  }
}

// Session admin simulée, comme dans App.test.tsx, plus les dix séries projets.
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
      respond: () => json({ role: 'admin', modules: { projects: 'view' } }),
    },
    ...panelRoutes(mode),
  ])
}

function renderProjects(mode: 'ok' | 'missing' | 'error' = 'ok') {
  stubEnvironment(mode)
  const router = createMemoryRouter(routes, { initialEntries: ['/projects'] })
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('ProjectsPage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('affiche les quatre KPI, les graphiques et les classements', async () => {
    renderProjects('ok')

    expect(await screen.findByRole('heading', { name: 'Tâches créées vs terminées' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Tâches par statut' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Tâches en retard' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Charge par personne' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Avancement moyen' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Délai moyen de livraison' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Jalons à venir' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Projets actifs' })).toBeInTheDocument()

    // Classements (dimensions `items`), statuts traduits et personnes fictives.
    expect(screen.getByText('À faire')).toBeInTheDocument()
    expect(screen.getByText('En cours')).toBeInTheDocument()
    expect(screen.getByText('Camille Moreau')).toBeInTheDocument()
    expect(screen.getByText('Recette finale')).toBeInTheDocument()

    // Mention obligatoire des données fictives (dépôt public, spec RGPD).
    expect(screen.getByText('Données de démonstration fictives')).toBeInTheDocument()
  })

  it('affiche l’état vide quand aucune série n’existe pour le module', async () => {
    renderProjects('missing')
    expect(
      await screen.findByText('Module projets & tâches pas encore connecté'),
    ).toBeInTheDocument()
  })

  it('affiche l’erreur et un bouton réessayer en cas de panne', async () => {
    renderProjects('error')
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('Impossible de charger les données')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Réessayer' })).toBeInTheDocument()
  })
})
