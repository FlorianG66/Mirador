// Page Paramètres (sous-phase 3d-b) : gestion de la double authentification.
// Active le TOTP (POST /auth/2fa/enable), affiche le QR et les codes de secours,
// ou le désactive (POST /auth/2fa/disable). Depuis 6c-iii, la page héberge aussi
// les règles d'alerte configurables.
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation } from '@tanstack/react-query'
import { AlertRulesPanel } from '../alertRules/AlertRulesPanel'
import { ApiError, api, unwrap } from '../api/client'
import { Button } from '../components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import { PageHeader } from '../components/ui/PageHeader'
import { PushToggle } from '../push/PushToggle.tsx'

interface SetupState {
  secret: string
  otpauthUrl: string
  backupCodes: string[]
}

export function SettingsPage() {
  const { t } = useTranslation()
  const [password, setPassword] = useState('')
  const [setup, setSetup] = useState<SetupState | null>(null)
  const [error, setError] = useState<string | null>(null)

  const enableMutation = useMutation({
    mutationFn: async (password: string) => {
      return unwrap(
        api.POST('/api/v1/auth/2fa/enable', { body: { current_password: password } }),
      )
    },
    onSuccess: (data) => {
      setSetup({ secret: data.secret, otpauthUrl: data.otpauth_url, backupCodes: data.backup_codes })
      setPassword('')
      setError(null)
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.detail || t('twoFactor.error') : t('twoFactor.error'))
    },
  })

  const disableMutation = useMutation({
    mutationFn: async (password: string) => {
      return unwrap(
        api.POST('/api/v1/auth/2fa/disable', { body: { current_password: password } }),
      )
    },
    onSuccess: () => {
      setSetup(null)
      setPassword('')
      setError(null)
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.detail || t('twoFactor.error') : t('twoFactor.error'))
    },
  })

  function handleEnable(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    enableMutation.mutate(password)
  }

  function handleDisable(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    disableMutation.mutate(password)
  }

  return (
    <div className="space-y-6 p-6">
      <PageHeader title={t('settings.title')} subtitle={t('settings.description')} />
      <Card className="max-w-lg">
        <CardHeader>
          <CardTitle>{t('twoFactor.title')}</CardTitle>
          <CardDescription>{t('twoFactor.settingsDescription')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {setup === null ? (
            <form onSubmit={handleEnable} className="space-y-4">
              <label className="block space-y-1 text-sm">
                <span className="font-medium">{t('twoFactor.password')}</span>
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
                <p role="alert" className="text-sm text-danger">{error}</p>
              )}
              <Button type="submit" disabled={enableMutation.isPending}>
                {enableMutation.isPending ? t('twoFactor.enabling') : t('twoFactor.enable')}
              </Button>
            </form>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-muted">{t('twoFactor.setupInstructions')}</p>
              <div className="rounded-md bg-muted p-3">
                <p className="text-xs font-medium text-muted">{t('twoFactor.secret')}</p>
                <p className="font-mono text-sm">{setup.secret}</p>
              </div>
              <div className="rounded-md bg-muted p-3">
                <p className="text-xs font-medium text-muted">{t('twoFactor.otpauthUrl')}</p>
                <p className="break-all font-mono text-xs">{setup.otpauthUrl}</p>
              </div>
              <div>
                <p className="text-sm font-medium">{t('twoFactor.backupCodes')}</p>
                <p className="text-xs text-muted">{t('twoFactor.backupCodesHint')}</p>
                <ul className="mt-2 grid grid-cols-2 gap-1">
                  {setup.backupCodes.map((code) => (
                    <li key={code} className="rounded bg-muted px-2 py-1 font-mono text-sm">
                      {code}
                    </li>
                  ))}
                </ul>
              </div>
              <form onSubmit={handleDisable} className="space-y-4 border-t pt-4">
                <label className="block space-y-1 text-sm">
                  <span className="font-medium">{t('twoFactor.password')}</span>
                  <input
                    type="password"
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="h-10 w-full rounded-md border border-border bg-background px-3 text-foreground outline-none focus-visible:ring-2 focus-visible:ring-brand"
                  />
                </label>
                <Button type="submit" variant="danger" disabled={disableMutation.isPending}>
                  {disableMutation.isPending ? t('twoFactor.disabling') : t('twoFactor.disable')}
                </Button>
              </form>
            </div>
          )}
        </CardContent>
      </Card>
      <AlertRulesPanel />
      <PushToggle />
    </div>
  )
}
