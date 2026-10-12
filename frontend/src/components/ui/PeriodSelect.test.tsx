// Test du sélecteur de période (phase 6a) : groupe accessible, option active
// marquée par aria-pressed et changement remonté à la page — le composant n'a
// aucun état interne.
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PeriodSelect } from './PeriodSelect.tsx'

const OPTIONS = [
  { value: 7, label: '7 j' },
  { value: 30, label: '30 j' },
  { value: 90, label: '90 j' },
]

describe('PeriodSelect', () => {
  it('marque la période active et remonte le changement', () => {
    const onChange = vi.fn()
    render(<PeriodSelect label="Période" options={OPTIONS} value={30} onChange={onChange} />)

    expect(screen.getByRole('group', { name: 'Période' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '30 j' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: '7 j' })).toHaveAttribute('aria-pressed', 'false')

    fireEvent.click(screen.getByRole('button', { name: '7 j' }))
    expect(onChange).toHaveBeenCalledWith(7)
  })
})
