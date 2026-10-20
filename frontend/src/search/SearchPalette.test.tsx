// Tests de la palette de recherche (sous-phase 6b-i) : ouverture par Ctrl+K et
// fermeture par Échap, filtrage des résultats, navigation au clavier ou au clic,
// et respect des permissions dans l'index proposé. L'i18n (FR) est initialisée
// par le setup partagé.
import { useState } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { describe, expect, it } from 'vitest'
import type { MyPermissionsOut } from '../api/types.ts'
import { SearchPalette } from './SearchPalette.tsx'

// Hôte minimal reproduisant le branchement de l'AppShell (props open/onOpen/onClose).
function Harness({ permissions }: { permissions: MyPermissionsOut | null }) {
  const [open, setOpen] = useState(false)
  return (
    <SearchPalette
      open={open}
      onOpen={() => setOpen(true)}
      onClose={() => setOpen(false)}
      permissions={permissions}
    />
  )
}

function renderPalette(permissions: MyPermissionsOut | null) {
  const router = createMemoryRouter(
    [
      { path: '/', element: <Harness permissions={permissions} /> },
      { path: '/finance', element: <div data-testid="finance-page" /> },
      { path: '/projects', element: <div data-testid="projects-page" /> },
    ],
    { initialEntries: ['/'] },
  )
  return render(<RouterProvider router={router} />)
}

function openPalette() {
  fireEvent.keyDown(window, { key: 'k', ctrlKey: true })
}

const ADMIN: MyPermissionsOut = { role: 'admin', modules: {} }
const MEMBER_WEB: MyPermissionsOut = { role: 'member', modules: { web: 'view' } }

describe('SearchPalette', () => {
  it('s’ouvre avec Ctrl+K, focalise la recherche et se ferme avec Échap', async () => {
    renderPalette(ADMIN)

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    openPalette()

    const dialog = await screen.findByRole('dialog')
    expect(dialog).toBeInTheDocument()
    expect(screen.getByRole('combobox')).toHaveFocus()

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('filtre les résultats et navigue vers le module avec Entrée', async () => {
    renderPalette(ADMIN)

    openPalette()
    const input = await screen.findByRole('combobox')
    fireEvent.change(input, { target: { value: 'finance' } })

    const labels = screen.getAllByRole('option').map((option) => option.textContent)
    // Par ordre d'index : la page Finance (libellé), puis les KPI dont le
    // module porteur est la finance (ligne secondaire).
    expect(labels[0]).toContain('Finance')
    expect(labels.some((label) => label?.includes("Chiffre d'affaires"))).toBe(true)

    fireEvent.keyDown(input, { key: 'Enter' })

    expect(await screen.findByTestId('finance-page')).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('déplace la sélection avec les flèches avant de valider', async () => {
    renderPalette(ADMIN)

    openPalette()
    const input = await screen.findByRole('combobox')
    fireEvent.change(input, { target: { value: 'finance' } })

    expect(screen.getAllByRole('option')[0]).toHaveAttribute('aria-selected', 'true')

    fireEvent.keyDown(input, { key: 'ArrowDown' })
    expect(screen.getAllByRole('option')[1]).toHaveAttribute('aria-selected', 'true')

    fireEvent.keyDown(input, { key: 'Enter' })
    expect(await screen.findByTestId('finance-page')).toBeInTheDocument()
  })

  it('navigue au clic sur un résultat', async () => {
    renderPalette(ADMIN)

    openPalette()
    const input = await screen.findByRole('combobox')
    fireEvent.change(input, { target: { value: 'projets' } })

    fireEvent.click(screen.getAllByRole('option')[0])

    expect(await screen.findByTestId('projects-page')).toBeInTheDocument()
  })

  it("ne montre pas les entrées d'un module sans permission", async () => {
    renderPalette(MEMBER_WEB)

    openPalette()
    const input = await screen.findByRole('combobox')
    fireEvent.change(input, { target: { value: 'finance' } })

    expect(screen.getByText('Aucun résultat')).toBeInTheDocument()
  })
})
