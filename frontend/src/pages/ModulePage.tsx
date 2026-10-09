// Page d'un module non encore développé (placeholder 3b). Le libellé vient de
// l'i18n selon la clé de module ; le contenu réel arrivera en phase 5.
import { Hammer } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { EmptyState } from '../components/ui/EmptyState.tsx'

export type ModuleKey =
  | 'finance'
  | 'analytics'
  | 'social'
  | 'projects'
  | 'legal'
  | 'team'

export interface ModulePageProps {
  moduleKey: ModuleKey
}

export function ModulePage({ moduleKey }: ModulePageProps) {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">{t(`nav.${moduleKey}`)}</h1>
      </header>
      <EmptyState
        icon={Hammer}
        title={t('placeholder.title')}
        description={t('placeholder.description')}
      />
    </div>
  )
}
