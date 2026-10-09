// Page de connexion (sous-phase 3d-a) : formulaire e-mail/mot de passe branché
// sur `POST /auth/login`. Les parcours A2F et OIDC complets arrivent en 3d-b.
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useLocation } from 'react-router'
import { useMutation } from '@tanstack/react-query'
import { ApiError, api, unwrap } from '../api/client'
import { useAuth } from '../auth/context'
import { Button } from '../components/ui/Button'

export function LoginPage() {
  const { t } = useTranslation()
  const { status, reload } = useAuth()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const mutation = useMutation({
    mutationFn: async (data: { email: string; password: string }) => {
      return unwrap(
        api.POST('/api/v1/auth/login', { body: data }),
      )
    },
    onSuccess: async () => {
      await reload()
    },
  })

  if (status === 'authenticated') {
    const from = (location.state as { from?: string } | null)?.from ?? '/'
    return <Navigate to={from} replace />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    mutation.mutate({ email, password })
  }

  const errorMessage = mutation.error
    ? mutation.error instanceof ApiError
      ? mutation.error.detail || t('login.error')
      : t('login.error')
    : null

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm space-y-4 rounded-lg border border-border bg-surface p-6 shadow-card"
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
        <div className="text-right">
          <Link to="/forgot-password" className="text-sm text-brand hover:underline">
            {t('login.forgotPassword')}
          </Link>
        </div>
        {errorMessage !== null && (
          <p role="alert" className="text-sm text-danger">
            {errorMessage}
          </p>
        )}
        <Button type="submit" className="w-full" disabled={mutation.isPending}>
          {mutation.isPending ? t('login.submitting') : t('login.submit')}
        </Button>
        <p className="text-center text-sm text-muted">
          <Link to="/register" className="text-brand hover:underline">
            {t('login.noAccount')}
          </Link>
        </p>
      </form>
    </main>
  )
}
