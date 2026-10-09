// Page réinitialisation du mot de passe (sous-phase 3d-a) : échange le jeton
// contre un nouveau mot de passe via `POST /auth/password/reset`.
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { useMutation } from '@tanstack/react-query'
import { api, ApiError, unwrap } from '../api/client'
import { Button } from '../components/ui/Button'

export function ResetPasswordPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const mutation = useMutation({
    mutationFn: async (data: { token: string; new_password: string }) => {
      return unwrap(
        api.POST('/api/v1/auth/password/reset', { body: data }),
      )
    },
    onSuccess: () => {
      navigate('/login', { replace: true })
    },
  })

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    mutation.mutate({ token, new_password: password })
  }

  const errorMessage = mutation.error
    ? mutation.error instanceof ApiError
      ? mutation.error.detail || t('resetPassword.error')
      : t('resetPassword.error')
    : password !== confirmPassword && confirmPassword !== ''
      ? t('resetPassword.mismatch')
      : null

  if (token === '') {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        <div className="w-full max-w-sm space-y-4 rounded-lg border border-border bg-surface p-6 text-center shadow-card">
          <h1 className="text-2xl font-semibold">{t('resetPassword.invalidTitle')}</h1>
          <p className="text-sm text-muted">{t('resetPassword.invalidDescription')}</p>
          <Link to="/forgot-password" className="text-brand hover:underline">
            {t('resetPassword.requestNew')}
          </Link>
        </div>
      </main>
    )
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm space-y-4 rounded-lg border border-border bg-surface p-6 shadow-card"
      >
        <div className="space-y-1 text-center">
          <h1 className="text-2xl font-semibold">{t('resetPassword.title')}</h1>
          <p className="text-sm text-muted">{t('resetPassword.description')}</p>
        </div>
        <label className="block space-y-1 text-left text-sm">
          <span className="font-medium">{t('resetPassword.password')}</span>
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
        <label className="block space-y-1 text-left text-sm">
          <span className="font-medium">{t('resetPassword.confirmPassword')}</span>
          <input
            type="password"
            autoComplete="new-password"
            required
            minLength={12}
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            className="h-10 w-full rounded-md border border-border bg-background px-3 text-foreground outline-none focus-visible:ring-2 focus-visible:ring-brand"
          />
        </label>
        {errorMessage !== null && (
          <p role="alert" className="text-sm text-danger">
            {errorMessage}
          </p>
        )}
        <Button type="submit" className="w-full" disabled={mutation.isPending}>
          {mutation.isPending ? t('resetPassword.submitting') : t('resetPassword.submit')}
        </Button>
        <p className="text-center text-sm text-muted">
          <Link to="/login" className="text-brand hover:underline">
            {t('resetPassword.backToLogin')}
          </Link>
        </p>
      </form>
    </main>
  )
}
