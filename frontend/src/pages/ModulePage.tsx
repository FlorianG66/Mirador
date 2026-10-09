// Page d'un module non encore d�velopp� (placeholder 3b). Le libell� vient de
// l'i18n selon la cl� de module ; le contenu r�el arrivera en phase 5.
import { Hammer } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { ModuleKey } from '../api/types.ts'
import { EmptyState } from '../components/ui/EmptyState.tsx'

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
