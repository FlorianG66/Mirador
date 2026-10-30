// Tests de la page Assistant (phase 8) : historique vide, envoi d'une question
// et affichage de la réponse, message traduit pour l'assistant non configuré
// (503) et pour le quota atteint (429). Appels API simulés, aucune donnée réelle.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AuthContext, type AuthContextValue } from '../auth/context.ts'
import { json, problem, stubFetch } from '../test/mockFetch.ts'
import { AssistantPage } from './AssistantPage.tsx'

const NOW = '2026-10-30T08:00:00Z'

const auth: AuthContextValue = {
  status: 'authenticated',
  user: null,
  activeOrganizationId: 'org1',
  permissions: null,
  reload: async () => undefined,
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <AuthContext.Provider value={auth}>
      <QueryClientProvider client={queryClient}>
        <AssistantPage />
      </QueryClientProvider>
    </AuthContext.Provider>,
  )
}

function stubChat(answer: () => Response) {
  stubFetch([
    {
      match: /chat\/messages$/,
      respond: (request) => (request.method === 'GET' ? json([]) : answer()),
    },
  ])
}

async function askQuestion(text: string) {
  fireEvent.change(await screen.findByLabelText('Votre question'), { target: { value: text } })
  fireEvent.click(screen.getByRole('button', { name: 'Envoyer' }))
}

describe('AssistantPage', () => {
  it('envoie une question et affiche la réponse', async () => {
    stubChat(() =>
      json(
        [
          { id: 'q1', role: 'user', content: 'Quel est mon CA ?', created_at: NOW },
          { id: 'a1', role: 'assistant', content: 'Votre CA est de 49 €.', created_at: NOW },
        ],
        201,
      ),
    )
    renderPage()

    expect(await screen.findByText(/Aucune question pour l'instant/)).toBeInTheDocument()
    await askQuestion('Quel est mon CA ?')

    expect(await screen.findByText('Votre CA est de 49 €.')).toBeInTheDocument()
    expect(screen.getByText('Quel est mon CA ?')).toBeInTheDocument()
  })

  it('signale un assistant non configuré', async () => {
    stubChat(() => problem(503, 'Assistant IA non configuré.'))
    renderPage()

    await askQuestion('Bonjour')

    expect(await screen.findByRole('alert')).toHaveTextContent("L'assistant n'est pas disponible")
  })

  it('signale le quota atteint', async () => {
    stubChat(() => problem(429, 'Quota quotidien de questions atteint.'))
    renderPage()

    await askQuestion('Bonjour')

    expect(await screen.findByRole('alert')).toHaveTextContent('quota')
  })
})
