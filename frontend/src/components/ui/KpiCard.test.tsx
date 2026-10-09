import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

// On force « réduire les animations » pour que le compteur affiche
// immédiatement sa cible (pas de requestAnimationFrame à attendre).
vi.mock('../../hooks/usePrefersReducedMotion.ts', () => ({
  usePrefersReducedMotion: () => true,
}))

import { KpiCard } from './KpiCard.tsx'

describe('KpiCard', () => {
  it('affiche le libellé, la valeur formatée et l’unité', () => {
    render(<KpiCard label="Chiffre d’affaires" value={12345} unit="€" />)
    expect(screen.getByText('Chiffre d’affaires')).toBeInTheDocument()
    expect(screen.getByText(/345/)).toBeInTheDocument()
    expect(screen.getByText('€')).toBeInTheDocument()
  })

  it('affiche une tendance positive signée', () => {
    render(<KpiCard label="Visiteurs" value={100} trend={12.5} />)
    expect(screen.getByText(/\+12,5/)).toBeInTheDocument()
  })
})
