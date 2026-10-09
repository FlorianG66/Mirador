// Page « Équipe » (phase 3c) : réservée aux admins via RequireAdmin. Le contenu
// réel (membres, invitations, permissions) arrivera dans une phase ultérieure.
import { Users } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { EmptyState } from '../components/ui/EmptyState.tsx'
import { PageHeader } from '../components/ui/PageHeader.tsx'

export function TeamPage() {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <PageHeader title={t('nav.team')} />
      <EmptyState
        icon={Users}
        title={t('placeholder.title')}
        description={t('placeholder.description')}
      />
    </div>
  )
}
