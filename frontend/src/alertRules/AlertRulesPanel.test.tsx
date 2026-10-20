// Tests du panneau des règles d'alerte (sous-phase 6c-iii) : liste avec seuil et
// état, création via le formulaire, activation/désactivation, suppression, état
// vide et droits (un membre sans écriture ne voit pas les actions). L'i18n (FR)
// est initialisée par le setup partagé ; les appels API sont simulés (aucune
// donnée réelle, AGENTS.md §5).
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { MyPermissionsOut } from '../api/types.ts'
import { AuthContext, type AuthContextValue } from '../auth/context.ts'
import { json, stubFetch, type FetchRoute } from '../test/mockFetch.ts'
import { AlertRulesPanel } from './AlertRulesPanel.tsx'

const NOW = '2026-10-19T08:00:00Z'

interface AlertRuleStub {
  id: string
  metric_key: string
  label: string | null
  comparison: 'above' | 'below'
  threshold: number
  period_days: number
  enabled: boolean
  created_at: string
  updated_at: string
}

function unpaidInvoices(overrides: Partial<AlertRuleStub> = {}): AlertRuleStub {
  return {
    id: 'r1',
    metric_key: 'finance.invoices_outstanding',
    label: 'Factures impayées',
    comparison: 'above',
    threshold: 5,
    period_days: 30,
    enabled: true,
    created_at: NOW,
    updated_at: NOW,
    ...overrides,
  }
}

/** Sink de test : la liste simulée évolue avec les écritures. */
interface RulesState {
  items: AlertRuleStub[]
  created: number
  patched: number
  deleted: number
}

function rulesRoutes(state: RulesState): FetchRoute[] {
  return [
    {
      match: /alert-rules\/[^/]+$/,
      respond: (request) => {
        if (request.method === 'DELETE') {
          state.deleted += 1
          return new Response(null, { status: 204 })
        }
        state.patched += 1
        return json(state.items[0])
      },
    },
    {
      match: /alert-rules$/,
      respond: (request) => {
        if (request.method === 'POST') {
          state.created += 1
          return json(
            unpaidInvoices({ id: 'r2', label: null, metric_key: 'finance.revenue' }),
            201,
          )
        }
        return json(state.items)
      },
    },
  ]
}

function permissionsWith(modules: Record<string, string>): MyPermissionsOut {
  return { role: 'member', modules } as MyPermissionsOut
}

function authValue(permissions: MyPermissionsOut | null): AuthContextValue {
  return {
    status: 'authenticated',
    user: null,
    activeOrganizationId: 'org1',
    permissions,
    reload: async () => undefined,
  }
}

function renderPanel(permissions: MyPermissionsOut | null = permissionsWith({ finance: 'edit' })) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return {
    queryClient,
    ...render(
      <AuthContext.Provider value={authValue(permissions)}>
        <QueryClientProvider client={queryClient}>
          <AlertRulesPanel />
        </QueryClientProvider>
      </AuthContext.Provider>,
    ),
  }
}

describe('AlertRulesPanel', () => {
  it('liste les règles avec le seuil et l’état activé', async () => {
    const state: RulesState = { items: [unpaidInvoices()], created: 0, patched: 0, deleted: 0 }
    stubFetch(rulesRoutes(state))

    renderPanel()

    expect(await screen.findByText('Factures impayées')).toBeInTheDocument()
    expect(screen.getByText(/Au-dessus de/)).toHaveTextContent('5')
    expect(screen.getByText('Activée')).toBeInTheDocument()
  })

  it('crée une règle via le formulaire', async () => {
    const state: RulesState = { items: [], created: 0, patched: 0, deleted: 0 }
    stubFetch(rulesRoutes(state))

    renderPanel()

    fireEvent.click(await screen.findByRole('button', { name: 'Nouvelle règle' }))
    fireEvent.change(screen.getByLabelText('Indicateur'), {
      target: { value: 'finance.revenue' },
    })
    fireEvent.change(screen.getByLabelText('Seuil'), { target: { value: '1000' } })
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))

    await waitFor(() => expect(state.created).toBe(1))
  })

  it('bascule une règle activée vers désactivée', async () => {
    const state: RulesState = { items: [unpaidInvoices()], created: 0, patched: 0, deleted: 0 }
    stubFetch(rulesRoutes(state))

    renderPanel()

    fireEvent.click(await screen.findByRole('button', { name: 'Désactiver' }))

    await waitFor(() => expect(state.patched).toBe(1))
  })

  it('supprime une règle après confirmation', async () => {
    const state: RulesState = { items: [unpaidInvoices()], created: 0, patched: 0, deleted: 0 }
    stubFetch(rulesRoutes(state))
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)

    renderPanel()

    fireEvent.click(await screen.findByRole('button', { name: 'Supprimer' }))

    await waitFor(() => expect(state.deleted).toBe(1))
    confirmSpy.mockRestore()
  })

  it('affiche un état vide sans règle', async () => {
    const state: RulesState = { items: [], created: 0, patched: 0, deleted: 0 }
    stubFetch(rulesRoutes(state))

    renderPanel()

    expect(await screen.findByText('Aucune règle définie')).toBeInTheDocument()
  })

  it('masque les actions quand le membre n’a pas le droit d’écrire', async () => {
    const state: RulesState = { items: [unpaidInvoices()], created: 0, patched: 0, deleted: 0 }
    stubFetch(rulesRoutes(state))

    renderPanel(permissionsWith({ finance: 'view' }))

    expect(await screen.findByText('Factures impayées')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Modifier' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Nouvelle règle' })).not.toBeInTheDocument()
  })
})
