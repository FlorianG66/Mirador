// Page « Équipe » (phase 3c) : réservée aux admins via RequireAdmin. Le contenu
// réel (membres, invitations, permissions) arrivera dans une phase ultérieure.
import { Users } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { EmptyState } from '../components/ui/EmptyState.tsx'

export function TeamPage() {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">{t('nav.team')}</h1>
      </header>
      <EmptyState
        icon={Users}
        title={t('placeholder.title')}
        description={t('placeholder.description')}
      />
    </div>
  )
}
