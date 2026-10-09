// Page d'inscription (sous-phase 3d-a) : crée le compte, l'organisation et le
// rattachement admin via `POST /auth/register`.
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router'
import { useMutation } from '@tanstack/react-query'
import { api, ApiError, unwrap } from '../api/client'
import { useAuth } from '../auth/context'
import { Button } from '../components/ui/Button'

export function RegisterPage() {
  const { t } = useTranslation()
  const { reload } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [organizationName, setOrganizationName] = useState('')
  const [siren, setSiren] = useState('')

  const mutation = useMutation({
    mutationFn: async (data: { email: string; password: string; organization_name: string; siren?: string }) => {
      return unwrap(
        api.POST('/api/v1/auth/register', { body: data }),
      )
    },
    onSuccess: async () => {
      await reload()
      navigate('/', { replace: true })
    },
  })

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    mutation.mutate({
      email,
      password,
      organization_name: organizationName,
      siren: siren || undefined,
    })
  }

  const errorMessage = mutation.error
    ? mutation.error instanceof ApiError
      ? mutation.error.detail || t('register.error')
      : t('register.error')
    : null

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm space-y-4 rounded-lg border border-border bg-surface p-6 shadow-card"
      >
        <div className="space-y-1 text-center">
          <h1 className="text-2xl font-semibold">{t('register.title')}</h1>
          <p className="text-sm text-muted">{t('register.description')}</p>
        </div>
        <label className="block space-y-1 text-left text-sm">
          <span className="font-medium">{t('register.organizationName')}</span>
          <input
            type="text"
            required
            value={organizationName}
            onChange={(event) => setOrganizationName(event.target.value)}
            className="h-10 w-full rounded-md border border-border bg-background px-3 text-foreground outline-none focus-visible:ring-2 focus-visible:ring-brand"
          />
        </label>
        <label className="block space-y-1 text-left text-sm">
          <span className="font-medium">{t('register.siren')}</span>
          <input
            type="text"
            maxLength={9}
            value={siren}
            onChange={(event) => setSiren(event.target.value.replace(/\D/g, ''))}
            placeholder="123456789"
            className="h-10 w-full rounded-md border border-border bg-background px-3 text-foreground outline-none focus-visible:ring-2 focus-visible:ring-brand"
          />
        </label>
        <label className="block space-y-1 text-left text-sm">
          <span className="font-medium">{t('register.email')}</span>
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="h-10 w-full rounded-md border border-border bg-background px-3 text-foreground outline-none focus-visible:ring-2 focus-visible:ring-brand"
          />
        </label>
        <label className="block space-y-1 text-left text-sm">
          <span className="font-medium">{t('register.password')}</span>
          <input
            type="password"
            autoComplete="new-password"
            required
            minLength={12}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="h-10 w-full rounded-md border border-border bg-background px-3 text-foreground outline-none focus-visible:ring-2 focus-visible:ring-brand"
          />
        </label>
        {errorMessage !== null && (
          <p role="alert" className="text-sm text-danger">
            {errorMessage}
          </p>
        )}
        <Button type="submit" className="w-full" disabled={mutation.isPending}>
          {mutation.isPending ? t('register.submitting') : t('register.submit')}
        </Button>
        <p className="text-center text-sm text-muted">
          <Link to="/login" className="text-brand hover:underline">
            {t('register.backToLogin')}
          </Link>
        </p>
      </form>
    </main>
  )
}
