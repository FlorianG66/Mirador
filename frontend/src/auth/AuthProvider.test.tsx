// Tests du contexte d'authentification (phase 3c) : chargement de la session,
// choix de l'organisation active (mémorisée ou première) et permissions.
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { ACTIVE_ORGANIZATION_KEY, AuthProvider } from './AuthProvider.tsx'
import { useAuth } from './context.ts'
import { json, problem, stubFetch, type FetchRoute } from '../test/mockFetch.ts'

const ADMIN_PERMISSIONS = {
  role: 'admin',
  modules: { finance: 'edit', web: 'edit', social: 'edit', projects: 'edit', legal: 'edit' },
}

function Probe() {
  const { status, user, activeOrganizationId, permissions, reload } = useAuth()
  return (
    <div>
      <p>{`statut:${status}`}</p>
      <p>{`email:${user?.email ?? '-'}`}</p>
      <p>{`organisation:${activeOrganizationId ?? '-'}`}</p>
      <p>{`finance:${permissions?.modules.finance ?? '-'}`}</p>
      <button type="button" onClick={() => void reload()}>
        recharger
      </button>
    </div>
  )
}

function renderProvider() {
  const router = createMemoryRouter(
    [{ path: '/', element: <AuthProvider />, children: [{ index: true, element: <Probe /> }] }],
    { initialEntries: ['/'] },
  )
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

describe('AuthProvider', () => {
  it('affiche l’état de chargement puis anonyme si la session est absente', async () => {
    stubFetch([{ match: /auth\/me$/, respond: () => problem(401, 'Non authentifié.') }])

    renderProvider()

    expect(screen.getByText('statut:loading')).toBeInTheDocument()
    expect(await screen.findByText('statut:anonymous')).toBeInTheDocument()
  })

  it('traite une panne réseau de /auth/me comme un état anonyme', async () => {
    stubFetch([
      {
        match: /auth\/me$/,
        respond: () => {
          throw new Error('réseau indisponible')
        },
      },
    ])

    renderProvider()

    expect(await screen.findByText('statut:anonymous')).toBeInTheDocument()
  })

  it('charge la session et les permissions de la première organisation', async () => {
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
      { match: /permissions$/, respond: () => json(ADMIN_PERMISSIONS) },
    ])

    renderProvider()

    expect(await screen.findByText('statut:authenticated')).toBeInTheDocument()
    expect(screen.getByText('email:admin@exemple.fr')).toBeInTheDocument()
    expect(screen.getByText('organisation:org1')).toBeInTheDocument()
    expect(screen.getByText('finance:edit')).toBeInTheDocument()
    expect(localStorage.getItem(ACTIVE_ORGANIZATION_KEY)).toBe('org1')
  })

  it('respecte l’organisation active mémorisée si elle est encore valide', async () => {
    localStorage.setItem(ACTIVE_ORGANIZATION_KEY, 'org2')
    const routes: FetchRoute[] = [
      {
        match: /auth\/me$/,
        respond: () =>
          json({
            id: 'u1',
            email: 'membre@exemple.fr',
            memberships: [
              { organization_id: 'org1', role: 'admin' },
              { organization_id: 'org2', role: 'member' },
            ],
          }),
      },
      { match: /organizations\/org2\/permissions$/, respond: () => json(ADMIN_PERMISSIONS) },
    ]
    stubFetch(routes)

    renderProvider()

    expect(await screen.findByText('organisation:org2')).toBeInTheDocument()
  })

  it('retombe sur la première organisation si la mémorisée est inconnue', async () => {
    localStorage.setItem(ACTIVE_ORGANIZATION_KEY, 'org-inconnue')
    stubFetch([
      {
        match: /auth\/me$/,
        respond: () =>
          json({
            id: 'u1',
            email: 'membre@exemple.fr',
            memberships: [{ organization_id: 'org1', role: 'member' }],
          }),
      },
      { match: /permissions$/, respond: () => json(ADMIN_PERMISSIONS) },
    ])

    renderProvider()

    expect(await screen.findByText('organisation:org1')).toBeInTheDocument()
    expect(localStorage.getItem(ACTIVE_ORGANIZATION_KEY)).toBe('org1')
  })

  it('passe en état d’erreur (rechargeable) si les permissions échouent', async () => {
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
      { match: /permissions$/, respond: () => problem(500, 'Erreur interne.') },
    ])

    renderProvider()

    expect(await screen.findByText('statut:error')).toBeInTheDocument()
  })
})
