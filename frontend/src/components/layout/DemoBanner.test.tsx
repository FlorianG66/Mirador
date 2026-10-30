// Tests du bandeau « Démo » : il n'apparaît que pour une organisation fictive et
// propose l'inscription (SPEC §9).
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { AuthContext, type AuthContextValue } from '../../auth/context.ts'
import { DemoBanner } from './DemoBanner.tsx'
import type { MeResponse } from '../../api/types'

function meResponse(isDemo: boolean): MeResponse {
  return {
    id: 'u1',
    email: 'demo@example.com',
    memberships: [
      {
        organization_id: 'org1',
        organization_name: 'Entreprise',
        role: 'admin',
        is_demo: isDemo,
        demo_sector: isDemo ? 'restaurant' : null,
      },
    ],
  }
}

function renderBanner(isDemo: boolean) {
  const value: AuthContextValue = {
    status: 'authenticated',
    user: meResponse(isDemo),
    activeOrganizationId: 'org1',
    permissions: null,
    reload: async () => undefined,
  }
  return render(
    <MemoryRouter>
      <AuthContext.Provider value={value}>
        <DemoBanner />
      </AuthContext.Provider>
    </MemoryRouter>,
  )
}

describe('DemoBanner', () => {
  it('affiche le rappel et le lien d’inscription en mode démo', () => {
    renderBanner(true)

    expect(screen.getByText('Mode démonstration')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Créer mon compte' })).toHaveAttribute(
      'href',
      '/register',
    )
  })

  it('reste invisible pour une vraie organisation', () => {
    renderBanner(false)

    expect(screen.queryByText('Mode démonstration')).not.toBeInTheDocument()
  })
})
