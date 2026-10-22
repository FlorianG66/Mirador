// Tests de la page publique de démonstration (phase 7) : choix du secteur,
// ouverture d'une session, lien à durée limitée et lien expiré. Stub fetch
// global + routeur mémoire, comme les autres pages.
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createMemoryRouter, RouterProvider, type RouteObject } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it } from 'vitest'
import { AuthProvider } from '../auth/AuthProvider.tsx'
import { DemoPage } from './DemoPage.tsx'
import { json, problem, stubFetch, type FetchRoute } from '../test/mockFetch.ts'

const SCENARIOS = [
  { key: 'restaurant', organization_name: 'Maison Fictive — Démo' },
  { key: 'agency', organization_name: 'Studio Fictif — Démo' },
  { key: 'ecommerce', organization_name: 'Boutique Fictive — Démo' },
]

const demoRoutes: RouteObject[] = [
  {
    element: <AuthProvider />,
    children: [
      { path: '/demo', element: <DemoPage /> },
      { path: '/demo/:token', element: <DemoPage /> },
      { path: '/', element: <p>Tableau de bord</p> },
      { path: '/login', element: <p>Connexion</p> },
    ],
  },
]

function renderDemo(path = '/demo', routes: FetchRoute[]) {
  const fetchMock = stubFetch(routes)
  const router = createMemoryRouter(demoRoutes, { initialEntries: [path] })
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return fetchMock
}

describe('DemoPage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('liste les scénarios et ouvre une session sur le secteur choisi', async () => {
    let meCalls = 0
    const fetchMock = renderDemo('/demo', [
      {
        match: /demo\/scenarios$/,
        respond: () => json(SCENARIOS),
      },
      {
        match: /demo\/sessions$/,
        respond: () => json({ sector: 'agency' }, 201),
      },
      {
        match: /auth\/me$/,
        respond: () => {
          meCalls += 1
          if (meCalls === 1) return problem(401, 'Non authentifié')
          return json({
            id: 'u1',
            email: 'demo@example.com',
            memberships: [
              {
                organization_id: 'org-demo',
                organization_name: 'Studio Fictif — Démo',
                role: 'admin',
                is_demo: true,
                demo_sector: 'agency',
              },
            ],
          })
        },
      },
      {
        match: /permissions$/,
        respond: () => json({ role: 'admin', modules: {} }),
      },
    ])

    expect(await screen.findByText('Studio Fictif — Démo')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Agence/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Ouvrir cette démo' }))

    expect(await screen.findByText('Tableau de bord')).toBeInTheDocument()
    const sessionCall = fetchMock.mock.calls.find(([input]) => {
      const request = input instanceof Request ? input : new Request(input)
      return new URL(request.url).pathname.endsWith('/demo/sessions')
    })
    expect(sessionCall).toBeDefined()
    const body = await (sessionCall![0] as Request).json()
    expect(body).toEqual({ sector: 'agency' })
  })

  it('échange un lien contre une session puis ouvre le tableau de bord', async () => {
    const fetchMock = renderDemo('/demo/jeton-fictif', [
      {
        match: /demo\/links\/jeton-fictif$/,
        respond: () => json({ sector: 'ecommerce' }, 201),
      },
      {
        match: /auth\/me$/,
        respond: () =>
          json({
            id: 'u2',
            email: 'demo2@example.com',
            memberships: [
              {
                organization_id: 'org-demo-2',
                organization_name: 'Boutique Fictive — Démo',
                role: 'admin',
                is_demo: true,
                demo_sector: 'ecommerce',
              },
            ],
          }),
      },
      {
        match: /permissions$/,
        respond: () => json({ role: 'admin', modules: {} }),
      },
    ])

    expect(await screen.findByText('Tableau de bord')).toBeInTheDocument()
    expect(
      fetchMock.mock.calls.some(([input]) => {
        const request = input instanceof Request ? input : new Request(input)
        return new URL(request.url).pathname.endsWith('/demo/links/jeton-fictif')
      }),
    ).toBe(true)
  })

  it('signale un lien expiré sans ouvrir de session', async () => {
    renderDemo('/demo/jeton-expire', [
      {
        match: /demo\/links\/jeton-expire$/,
        respond: () => problem(410, 'Lien inconnu ou expiré'),
      },
      {
        match: /auth\/me$/,
        respond: () => problem(401, 'Non authentifié'),
      },
    ])

    expect(
      await screen.findByText('Ce lien de démonstration est inconnu ou a expiré.'),
    ).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.queryByText('Tableau de bord')).not.toBeInTheDocument()
    })
  })

  it('affiche une erreur quand les scénarios ne se chargent pas', async () => {
    renderDemo('/demo', [
      {
        match: /demo\/scenarios$/,
        respond: () => problem(500, 'Panne'),
      },
      {
        match: /auth\/me$/,
        respond: () => problem(401, 'Non authentifié'),
      },
    ])

    expect(
      await screen.findByText('Impossible d’ouvrir la démonstration pour le moment.'),
    ).toBeInTheDocument()
  })
})
