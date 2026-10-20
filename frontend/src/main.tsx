import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App.tsx'
import { PROJECT_NAME } from './constants.ts'
import './i18n/index.ts'
import './index.css'
import { registerServiceWorker } from './push/register.ts'

document.title = PROJECT_NAME

// Service worker Web Push (production uniquement, sans effet ailleurs) : il est
// enregistré tôt pour être prêt quand l'utilisateur active les notifications.
void registerServiceWorker()

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
