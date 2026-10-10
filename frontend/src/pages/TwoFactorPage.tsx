// Page de défi 2FA (sous-phase 3d-b) : échange le code TOTP ou un code de
// secours contre une session complète via `POST /auth/2fa/verify`.
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useLocation } from 'react-router'
import { useMutation } from '@tanstack/react-query'
import { ApiError, api, unwrap } from '../api/client'
import { useAuth } from '../auth/context'
import { Button } from '../components/ui/Button'

export function TwoFactorPage() {
  const { t } = useTranslation()
  const { status, reload } = useAuth()
  const location = useLocation()
  const [code, setCode] = useState('')

  const mutation = useMutation({
    mutationFn: async (code: string) => {
      return unwrap(
        api.POST('/api/v1/auth/2fa/verify', { body: { code } }),
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

  if (status !== 'anonymous') {
    return <Navigate to="/login" replace />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    mutation.mutate(code)
  }

  const errorMessage = mutation.error
    ? mutation.error instanceof ApiError
      ? mutation.error.detail || t('twoFactor.error')
      : t('twoFactor.error')
    : null

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm space-y-4 rounded-lg border border-border bg-surface p-6 shadow-card"
      >
        <div className="space-y-1 text-center">
          <h1 className="text-2xl font-semibold">{t('twoFactor.title')}</h1>
          <p className="text-sm text-muted">{t('twoFactor.description')}</p>
        </div>
        <label className="block space-y-1 text-left text-sm">
          <span className="font-medium">{t('twoFactor.code')}</span>
          <input
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            required
            value={code}
            onChange={(event) => setCode(event.target.value)}
            placeholder="123456"
            className="h-10 w-full rounded-md border border-border bg-background px-3 text-center text-lg tracking-widest text-foreground outline-none focus-visible:ring-2 focus-visible:ring-brand"
          />
        </label>
        {errorMessage !== null && (
          <p role="alert" className="text-sm text-danger">
            {errorMessage}
          </p>
        )}
        <Button type="submit" className="w-full" disabled={mutation.isPending}>
          {mutation.isPending ? t('twoFactor.submitting') : t('twoFactor.submit')}
        </Button>
        <p className="text-center text-sm text-muted">
          {t('twoFactor.backupCodeHint')}
        </p>
      </form>
    </main>
  )
}
