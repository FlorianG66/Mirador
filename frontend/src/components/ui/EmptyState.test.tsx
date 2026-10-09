import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EmptyState } from './EmptyState.tsx'

describe('EmptyState', () => {
  it('affiche le titre et la description', () => {
    render(<EmptyState title="Rien à afficher" description="Revenez plus tard." />)
    expect(screen.getByText('Rien à afficher')).toBeInTheDocument()
    expect(screen.getByText('Revenez plus tard.')).toBeInTheDocument()
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})
