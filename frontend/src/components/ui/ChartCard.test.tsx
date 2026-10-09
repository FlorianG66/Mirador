import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ChartCard } from './ChartCard.tsx'

describe('ChartCard', () => {
  it('affiche l’état vide quand empty est vrai', () => {
    render(<ChartCard title="Revenus" empty emptyTitle="Aucune donnée" />)
    expect(screen.getByText('Revenus')).toBeInTheDocument()
    expect(screen.getByText('Aucune donnée')).toBeInTheDocument()
  })

  it('n’affiche pas le contenu vide en chargement', () => {
    render(
      <ChartCard title="Revenus" loading emptyTitle="Aucune donnée">
        <p>Graphique</p>
      </ChartCard>,
    )
    expect(screen.queryByText('Aucune donnée')).not.toBeInTheDocument()
    expect(screen.queryByText('Graphique')).not.toBeInTheDocument()
  })
})
