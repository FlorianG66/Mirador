// Page « Vue d'ensemble » (placeholder 3b) : présente la grille de widgets et
// leurs états vides. Aucune donnée n'est inventée ici (AGENTS.md §8) — chaque
// carte sera branchée sur l'API du module à sa phase.
import { useTranslation } from 'react-i18next'
import { ChartCard } from '../components/ui/ChartCard.tsx'

const WIDGETS = [
  { key: 'finance', titleKey: 'nav.finance' },
  { key: 'analytics', titleKey: 'nav.analytics' },
  { key: 'social', titleKey: 'nav.social' },
  { key: 'projects', titleKey: 'nav.projects' },
] as const

export function DashboardPage() {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold">{t('dashboard.title')}</h1>
        <p className="text-sm text-muted">{t('dashboard.subtitle')}</p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2">
        {WIDGETS.map((widget) => (
          <ChartCard
            key={widget.key}
            title={t(widget.titleKey)}
            empty
            emptyTitle={t('emptyState.title')}
            emptyDescription={t('emptyState.description')}
          />
        ))}
      </div>
    </div>
  )
}
