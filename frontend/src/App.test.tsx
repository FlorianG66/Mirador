import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { beforeEach, describe, expect, it } from 'vitest'
import { routes } from './app/routes.tsx'
import { json, stubFetch } from './test/mockFetch.ts'

// Session admin simulée : toutes les routes de la coquille sont protégées, il
// faut donc un état authentifié + permissions pour les rendre.
beforeEach(() => {
  localStorage.clear()
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
      respond: () =>
        json({
          role: 'admin',
          modules: {
            finance: 'edit',
            web: 'edit',
            social: 'edit',
            projects: 'edit',
            legal: 'edit',
          },
        }),
    },
  ])
})

// Rend l'application à un chemin donné via un routeur mémoire (déterministe,
// indépendant de l'historique du navigateur).
function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  return render(<RouterProvider router={router} />)
}

describe('App (coquille)', () => {
  it("affiche le nom du projet et la navigation principale", async () => {
    renderAt('/')
    expect(await screen.findByText('Mirador')).toBeInTheDocument()
    expect(
      screen.getByRole('navigation', { name: /navigation principale/i }),
    ).toBeInTheDocument()
  })

  it("affiche la vue d'ensemble sur la route racine", async () => {
    renderAt('/')
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent(/ensemble/i)
  })

  it('marque le module courant comme actif', async () => {
    renderAt('/finance')
    expect(await screen.findByRole('link', { name: 'Finance' })).toHaveAttribute(
      'aria-current',
      'page',
    )
  })

  it('affiche la page 404 sur une route inconnue', async () => {
    renderAt('/route-inconnue')
    expect(await screen.findByText(/page introuvable/i)).toBeInTheDocument()
  })
})
