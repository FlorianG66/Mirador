// Page mot de passe oublié (sous-phase 3d-a) : envoie un e-mail de réinitialisation
// via `POST /auth/password/forgot`. La réponse est toujours identique (anti-énumération).
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { useMutation } from '@tanstack/react-query'
import { api, unwrap } from '../api/client'
import { Button } from '../components/ui/Button'

export function ForgotPasswordPage() {
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)

  const mutation = useMutation({
    mutationFn: async (email: string) => {
      return unwrap(
        api.POST('/api/v1/auth/password/forgot', { body: { email } }),
      )
    },
    onSuccess: () => {
      setSent(true)
    },
  })

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    mutation.mutate(email)
  }

  if (sent) {
    return (
      <main className="flex min-h-screen items-center justify-center p-6">
        <div className="w-full max-w-sm space-y-4 rounded-lg border border-border bg-surface p-6 text-center shadow-card">
          <h1 className="text-2xl font-semibold">{t('forgotPassword.sentTitle')}</h1>
          <p className="text-sm text-muted">{t('forgotPassword.sentDescription')}</p>
          <Link to="/login" className="text-brand hover:underline">
            {t('forgotPassword.backToLogin')}
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
          <h1 className="text-2xl font-semibold">{t('forgotPassword.title')}</h1>
          <p className="text-sm text-muted">{t('forgotPassword.description')}</p>
        </div>
        <label className="block space-y-1 text-left text-sm">
          <span className="font-medium">{t('forgotPassword.email')}</span>
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="h-10 w-full rounded-md border border-border bg-background px-3 text-foreground outline-none focus-visible:ring-2 focus-visible:ring-brand"
          />
        </label>
        {mutation.isError && (
          <p role="alert" className="text-sm text-danger">
            {t('forgotPassword.error')}
          </p>
        )}
        <Button type="submit" className="w-full" disabled={mutation.isPending}>
          {mutation.isPending ? t('forgotPassword.submitting') : t('forgotPassword.submit')}
        </Button>
        <p className="text-center text-sm text-muted">
          <Link to="/login" className="text-brand hover:underline">
            {t('forgotPassword.backToLogin')}
          </Link>
        </p>
      </form>
    </main>
  )
}
