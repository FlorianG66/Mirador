// Réglage « notifications hors onglet » (sous-phase 6c-iii-b), affiché dans les
// paramètres à côté des règles d'alerte. Il pilote l'abonnement Web Push du
// navigateur courant : chaque appareil a son propre abonnement. Tous les textes
// viennent de l'i18n (AGENTS.md §7) ; aucune donnée réelle n'est manipulée.
import { BellRing, BellOff } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '../components/ui/Button.tsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card.tsx'
import { usePushSubscription } from './usePushSubscription.ts'

export function PushToggle() {
  const { t } = useTranslation()
  const { status, busy, error, enable, disable } = usePushSubscription()

  // Le navigateur ne sait pas faire de Web Push : on l'explique au lieu d'un
  // bouton inerte (et on n'affiche rien pendant la lecture de l'état).
  if (status === 'loading') return null

  const active = status === 'enabled'

  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>{t('push.title')}</CardTitle>
        <CardDescription>{t('push.description')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted">{t(statusDescriptionKey(status))}</p>
        {error !== null ? (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        ) : null}
        {status === 'unsupported' || status === 'unavailable' || status === 'denied' ? null : (
          <Button
            variant={active ? 'secondary' : 'primary'}
            disabled={busy}
            onClick={() => void (active ? disable() : enable())}
          >
            {active ? <BellOff className="size-4" /> : <BellRing className="size-4" />}
            {busy
              ? t(active ? 'push.disabling' : 'push.enabling')
              : t(active ? 'push.disable' : 'push.enable')}
          </Button>
        )}
      </CardContent>
    </Card>
  )
}

/** Clé i18n décrivant l'état courant (jamais un texte figé). */
function statusDescriptionKey(status: string): string {
  switch (status) {
    case 'enabled':
      return 'push.statusEnabled'
    case 'denied':
      return 'push.statusDenied'
    case 'unsupported':
      return 'push.statusUnsupported'
    case 'unavailable':
      return 'push.statusUnavailable'
    default:
      return 'push.statusDisabled'
  }
}
