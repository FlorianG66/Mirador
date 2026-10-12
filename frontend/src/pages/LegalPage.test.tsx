// Tests de la page Fiche légale (sous-phase 5e-c) : fiche complète (admin),
// dirigeants masqués pour un membre, panne réseau, et saisie manuelle n'envoyant
// que les champs modifiés. Même approche que ProjectsPage.test.tsx : routeur
// mémoire + stub fetch global + QueryClient sans retry.
import { fireEvent, render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it } from 'vitest'
import { routes } from '../app/routes.tsx'
import { json, stubFetch, type FetchRoute } from '../test/mockFetch.ts'

/** Fiche légale fictive (jamais d'entreprise réelle). */
const PROFILE = {
  siren: '732829320',
  siret_siege: '73282932000017',
  raison_sociale: 'Démo Conseil SAS',
  nom_commercial: 'Démo Conseil',
  forme_juridique: 'SAS',
  date_creation: '2018-04-12',
  code_naf: '6201Z',
  libelle_naf: 'Programmation informatique',
  adresse_siege: '12 rue de la Paix, 75002 Paris',
  tranche_effectif: '20 à 49 salariés',
  capital_social: '10000',
  rcs_greffe: 'RCS Paris 732 829 320',
  dirigeants: [{ nom: 'Camille Moreau', qualite: 'Présidente' }],
  sources: {
    raison_sociale: { source: 'registry', synced_at: '2026-10-01T09:00:00Z' },
    siren: { source: 'registry', synced_at: '2026-10-01T09:00:00Z' },
    adresse_siege: { source: 'manual', synced_at: '2026-10-02T10:00:00Z' },
  },
  identifiers: [
    {
      pays: 'FR',
      schema: 'vat',
      valeur: 'FR44732829320',
      source: 'computed',
      verified_at: null,
    },
  ],
  updated_at: '2026-10-02T10:00:00Z',
}

// Session simulée pour la fiche légale, avec un profil et un niveau d'accès.
function stubEnvironment(
  mode: 'ok' | 'member' | 'error',
  onPut?: (request: Request) => void,
) {
  const role = mode === 'member' ? 'member' : 'admin'
  const profile = mode === 'member' ? { ...PROFILE, dirigeants: undefined } : PROFILE
  const fetchRoutes: FetchRoute[] = [
    {
      match: /auth\/me$/,
      respond: () =>
        json({
          id: 'u1',
          email: 'admin@exemple.fr',
          memberships: [{ organization_id: 'org1', role }],
        }),
    },
    {
      match: /permissions$/,
      respond: () => json({ role, modules: { legal: mode === 'member' ? 'view' : 'edit' } }),
    },
    {
      match: /legal$/,
      respond: (request) => {
        if (mode === 'error') {
          throw new Error('panne réseau simulée')
        }
        if (request.method === 'PUT') {
          onPut?.(request)
        }
        return json(profile)
      },
    },
  ]
  stubFetch(fetchRoutes)
}

function renderLegal(mode: 'ok' | 'member' | 'error' = 'ok', onPut?: (request: Request) => void) {
  stubEnvironment(mode, onPut)
  const router = createMemoryRouter(routes, { initialEntries: ['/legal'] })
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('LegalPage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('affiche la fiche, la provenance, les dirigeants et les mentions légales', async () => {
    renderLegal('ok')

    expect(await screen.findByText('Démo Conseil SAS')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Identité légale' })).toBeInTheDocument()
    expect(screen.getByText('732829320')).toBeInTheDocument()
    expect(screen.getByText('FR44732829320')).toBeInTheDocument()
    expect(screen.getByText('Camille Moreau')).toBeInTheDocument()
    expect(screen.getByText('Présidente')).toBeInTheDocument()

    // Provenance : au moins un champ issu du registre est signalé.
    expect(screen.getAllByText('Registre').length).toBeGreaterThan(0)

    // Bloc mentions légales assemblé (SIREN/SIRET/TVA dans un même texte).
    expect(screen.getByText(/SIREN : 732829320/)).toBeInTheDocument()
    expect(screen.getByText(/TVA intracommunautaire : FR44732829320/)).toBeInTheDocument()

    // L'admin peut rafraîchir et modifier.
    expect(screen.getByRole('button', { name: /Rafraîchir depuis le registre/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Modifier' })).toBeInTheDocument()
  })

  it('masque les dirigeants et les actions d’édition pour un membre', async () => {
    renderLegal('member')

    expect(
      await screen.findByText('Les dirigeants sont visibles par les administrateurs.'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Modifier' })).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /Rafraîchir depuis le registre/ }),
    ).not.toBeInTheDocument()
  })

  it('affiche un état d’erreur réessayable en cas de panne', async () => {
    renderLegal('error')

    expect(await screen.findByText('Impossible de charger la fiche légale. Réessayez dans un instant.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Réessayer' })).toBeInTheDocument()
  })

  it('n’envoie que les champs modifiés lors d’une saisie manuelle', async () => {
    let putRequest: Request | null = null
    renderLegal('ok', (request) => {
      putRequest = request
    })

    fireEvent.click(await screen.findByRole('button', { name: 'Modifier' }))
    const reasonInput = screen.getByLabelText('Raison sociale')
    fireEvent.change(reasonInput, { target: { value: 'Nouvelle Raison SAS' } })
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))

    expect(await screen.findByText('Modifications enregistrées.')).toBeInTheDocument()
    expect(putRequest).not.toBeNull()
    const body = await putRequest!.json()
    expect(body).toEqual({ raison_sociale: 'Nouvelle Raison SAS' })
  })
})
