// Tests de l'en-tête de page et de l'export PDF (sous-phase 6c-i) : un seul
// titre de niveau 1 (le bandeau imprimable ne le duplique pas), bouton d'export
// présent uniquement avec `printable`, rappel de période, et appel effectif à
// l'impression du navigateur. Aucun rendu graphique ici.
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PageHeader } from './PageHeader.tsx'

describe('PageHeader', () => {
  it('affiche un seul titre de niveau 1', () => {
    render(<PageHeader title="Finance" subtitle="Vue financière" />)

    const headings = screen.getAllByRole('heading', { level: 1 })
    expect(headings).toHaveLength(1)
    expect(headings[0]).toHaveTextContent('Finance')
    expect(screen.getByText('Vue financière')).toBeInTheDocument()
  })

  it("n'affiche pas d'export PDF sans l'option printable", () => {
    render(<PageHeader title="Finance" />)

    expect(
      screen.queryByRole('button', { name: 'Exporter en PDF' }),
    ).not.toBeInTheDocument()
  })

  it("ajoute l'export PDF et rappelle la période sur le document imprimé", () => {
    render(<PageHeader title="Finance" printable printPeriod="30 j" />)

    expect(screen.getByRole('button', { name: 'Exporter en PDF' })).toBeInTheDocument()
    expect(screen.getByText(/Période : 30 j/)).toBeInTheDocument()
  })

  it("déclenche l'impression du navigateur au clic sur l'export", () => {
    const print = vi.fn()
    vi.stubGlobal('print', print)
    render(<PageHeader title="Finance" printable />)

    fireEvent.click(screen.getByRole('button', { name: 'Exporter en PDF' }))

    expect(print).toHaveBeenCalledTimes(1)
  })
})
