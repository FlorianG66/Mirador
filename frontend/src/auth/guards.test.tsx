// Tests des gardes de routes (phase 3c) : redirection si non connecté, refus
// hors permission (403), accès admin, filtre du menu latéral et état de chargement.
import { render, screen, within } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { routes } from '../app/routes.tsx'
import { json, problem, stubFetch, type FetchRoute } from '../test/mockFetch.ts'

const ADMIN = {
  role: 'admin',
  modules: { finance: 'edit', web: 'edit', social: 'edit', projects: 'edit', legal: 'edit' },
}

const MEMBER = {
  role: 'member',
  modules: {
    finance: 'view',
    web: 'none',
    social: 'none',
    projects: 'none',
    legal: 'none',
  },
}

function sessionRoutes(permissions: typeof ADMIN, email = 'membre@exemple.fr'): FetchRoute[] {
  return [
    {
      match: /auth\/me$/,
      respond: () =>
        json({
          id: 'u1',
          email,
          memberships: [{ organization_id: 'org1', role: permissions.role }],
        }),
    },
    { match: /permissions$/, respond: () => json(permissions) },
  ]
}

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  localStorage.clear()
})

describe('gardes de routes', () => {
  it('affiche l’état de chargement pendant l’amorçage de la session', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => undefined)))

    renderAt('/')

    expect(screen.getByText(/chargement/i)).toBeInTheDocument()
  })

  it('redirige un visiteur non connecté vers la connexion', async () => {
    stubFetch([{ match: /auth\/me$/, respond: () => problem(401, 'Non authentifié.') }])

    renderAt('/finance')

    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument()
  })

  it('refuse (403) un module sans permission de lecture', async () => {
    stubFetch(sessionRoutes(MEMBER))

    renderAt('/web')

    expect(
      await screen.findByRole('heading', { name: 'Accès refusé' }),
    ).toBeInTheDocument()
  })

  it('affiche le module quand le membre a la permission de lecture', async () => {
    stubFetch(sessionRoutes(MEMBER))

    renderAt('/finance')

    // La sous-phase 5a remplace le placeholder finance par la vraie page : on
    // vérifie que le module se rend (titre de page), pas son contenu métier.
    expect(await screen.findByRole('heading', { level: 1, name: 'Finance' })).toBeInTheDocument()
  })

  it('réserve la page Équipe aux admins', async () => {
    stubFetch(sessionRoutes(MEMBER))

    renderAt('/team')

    expect(
      await screen.findByRole('heading', { name: 'Accès refusé' }),
    ).toBeInTheDocument()
  })

  it('autorise l’admin sur la page Équipe', async () => {
    stubFetch(sessionRoutes(ADMIN, 'admin@exemple.fr'))

    renderAt('/team')

    expect(await screen.findByRole('heading', { name: 'Équipe' })).toBeInTheDocument()
  })

  it('masque du menu les modules sans accès et réserve Équipe à l’admin', async () => {
    stubFetch(sessionRoutes(MEMBER))

    renderAt('/')

    const nav = await screen.findByRole('navigation', { name: /navigation principale/i })
    expect(within(nav).getByRole('link', { name: 'Finance' })).toBeInTheDocument()
    expect(within(nav).queryByRole('link', { name: 'Web analytics' })).not.toBeInTheDocument()
    expect(within(nav).queryByRole('link', { name: 'Équipe' })).not.toBeInTheDocument()
  })

  it('montre tous les modules et Équipe à l’admin', async () => {
    stubFetch(sessionRoutes(ADMIN, 'admin@exemple.fr'))

    renderAt('/')

    const nav = await screen.findByRole('navigation', { name: /navigation principale/i })
    expect(within(nav).getByRole('link', { name: 'Web analytics' })).toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: 'Équipe' })).toBeInTheDocument()
  })
})
