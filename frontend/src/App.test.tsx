import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { describe, expect, it } from 'vitest'
import { routes } from './app/routes.tsx'

// Rend l'application à un chemin donné via un routeur mémoire (déterministe,
// indépendant de l'historique du navigateur).
function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  return render(<RouterProvider router={router} />)
}

describe('App (coquille)', () => {
  it('affiche le nom du projet et la navigation principale', () => {
    renderAt('/')
    expect(screen.getByText('Mirador')).toBeInTheDocument()
    expect(
      screen.getByRole('navigation', { name: /navigation principale/i }),
    ).toBeInTheDocument()
  })

  it('affiche la vue d’ensemble sur la route racine', () => {
    renderAt('/')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      /vue d’ensemble/i,
    )
  })

  it('marque le module courant comme actif', () => {
    renderAt('/finance')
    expect(screen.getByRole('link', { name: 'Finance' })).toHaveAttribute(
      'aria-current',
      'page',
    )
  })

  it('affiche la page 404 sur une route inconnue', () => {
    renderAt('/route-inconnue')
    expect(screen.getByText(/page introuvable/i)).toBeInTheDocument()
  })
})
