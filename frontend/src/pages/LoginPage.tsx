// Page de connexion (phase 3c) : coquille minimale hors AppShell. Le formulaire
// complet (A2F, OIDC) arrive avec la phase d'authentification côté front.
import { useTranslation } from 'react-i18next'
import { Navigate, useLocation } from 'react-router'
import { useAuth } from '../auth/context.ts'

export function LoginPage() {
  const { t } = useTranslation()
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'authenticated') {
    const from = (location.state as { from?: string } | null)?.from ?? '/'
    return <Navigate to={from} replace />
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm space-y-2 rounded-lg border border-border bg-surface p-6 text-center">
        <h1 className="text-2xl font-semibold">{t('login.title')}</h1>
        <p className="text-sm text-muted">{t('login.description')}</p>
      </div>
    </main>
  )
}
