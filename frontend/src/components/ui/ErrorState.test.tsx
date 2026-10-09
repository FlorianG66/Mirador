import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ErrorState } from './ErrorState.tsx'

describe('ErrorState', () => {
  it('annonce l’erreur et déclenche le réessai', () => {
    const onRetry = vi.fn()
    render(<ErrorState title="Erreur" retryLabel="Réessayer" onRetry={onRetry} />)

    expect(screen.getByRole('alert')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Réessayer' }))
    expect(onRetry).toHaveBeenCalledOnce()
  })
})
