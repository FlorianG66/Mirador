// Page d'un module non encore développé (placeholder 3b). Le libellé vient de
// l'i18n selon la clé de module ; le contenu réel arrivera en phase 5.
import { Hammer } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { ModuleKey } from '../api/types.ts'
import { EmptyState } from '../components/ui/EmptyState.tsx'
import { PageHeader } from '../components/ui/PageHeader.tsx'

export interface ModulePageProps {
  moduleKey: ModuleKey
}

export function ModulePage({ moduleKey }: ModulePageProps) {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <PageHeader title={t(`nav.${moduleKey}`)} />
      <EmptyState
        icon={Hammer}
        title={t('placeholder.title')}
        description={t('placeholder.description')}
      />
    </div>
  )
}
