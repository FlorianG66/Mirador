// Page de connexion (phase 3c) : formulaire e-mail/mot de passe branché sur
// `POST /auth/login`. Les parcours A2F et OIDC complets arrivent en 3d.
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useLocation } from 'react-router'
import { ApiError, api } from '../api/client.ts'
import { useAuth } from '../auth/context.ts'
import { Button } from '../components/ui/Button.tsx'

export function LoginPage() {
  const { t } = useTranslation()
  const { status, reload } = useAuth()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (status === 'authenticated') {
    const from = (location.state as { from?: string } | null)?.from ?? '/'
    return <Navigate to={from} replace />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const result = await api.POST('/api/v1/auth/login', {
        body: { email, password },
      })
      if (!result.response.ok) {
        throw ApiError.from(result.response.status, result.error)
      }
      if (result.data?.totp_required) {
        setError(t('login.totpUnsupported'))
        return
      }
      await reload()
    } catch {
      setError(t('login.error'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm space-y-4 rounded-lg border border-border bg-surface p-6"
      >
        <div className="space-y-1 text-center">
          <h1 className="text-2xl font-semibold">{t('login.title')}</h1>
          <p className="text-sm text-muted">{t('login.description')}</p>
        </div>
        <label className="block space-y-1 text-left text-sm">
          <span className="font-medium">{t('login.email')}</span>
          <input
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="h-10 w-full rounded-md border border-border bg-background px-3 text-foreground outline-none focus-visible:ring-2 focus-visible:ring-brand"
          />
        </label>
        <label className="block space-y-1 text-left text-sm">
          <span className="font-medium">{t('login.password')}</span>
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="h-10 w-full rounded-md border border-border bg-background px-3 text-foreground outline-none focus-visible:ring-2 focus-visible:ring-brand"
          />
        </label>
        {error !== null && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}
        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? t('login.submitting') : t('login.submit')}
        </Button>
      </form>
    </main>
  )
}
