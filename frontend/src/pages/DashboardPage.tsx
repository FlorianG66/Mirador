// Page « Vue d'ensemble » : disposition « bento » asymétrique (colonnes 7/5).
// Aucune donnée n'est inventée ici (AGENTS.md §8) — le panneau d'accueil sert de
// navigation rapide réelle vers les modules autorisés, le reste affiche des
// états vides soignés en attendant les API des modules.
import type { LucideIcon } from 'lucide-react'
import {
  ArrowRight,
  BarChart3,
  History,
  Landmark,
  ListChecks,
  Share2,
  Wallet,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import type { ModuleKey } from '../api/types.ts'
import { useAuth } from '../auth/context.ts'
import { Card, CardHeader, CardTitle } from '../components/ui/Card.tsx'
import { ChartCard } from '../components/ui/ChartCard.tsx'
import { EmptyState } from '../components/ui/EmptyState.tsx'
import { PageHeader } from '../components/ui/PageHeader.tsx'
import { canSeeModule } from '../lib/permissions.ts'
import { cn } from '../lib/utils.ts'

interface ModuleEntry {
  moduleKey: ModuleKey
  to: string
  icon: LucideIcon
}

const MODULES: ModuleEntry[] = [
  { moduleKey: 'finance', to: '/finance', icon: Wallet },
  { moduleKey: 'web', to: '/web', icon: BarChart3 },
  { moduleKey: 'social', to: '/social', icon: Share2 },
  { moduleKey: 'projects', to: '/projects', icon: ListChecks },
  { moduleKey: 'legal', to: '/legal', icon: Landmark },
]

// Répartition volontairement asymétrique (7/5 puis 5/7) pour casser la symétrie.
const WIDGETS: { key: string; titleKey: string; span: string }[] = [
  { key: 'finance', titleKey: 'nav.finance', span: 'xl:col-span-7' },
  { key: 'web', titleKey: 'nav.web', span: 'xl:col-span-5' },
  { key: 'social', titleKey: 'nav.social', span: 'xl:col-span-5' },
  { key: 'projects', titleKey: 'nav.projects', span: 'xl:col-span-7' },
]

export function DashboardPage() {
  const { t } = useTranslation()
  const { permissions } = useAuth()
  const visibleModules = MODULES.filter((entry) =>
    canSeeModule(entry.moduleKey, permissions),
  )

  return (
    <div className="space-y-6">
      <PageHeader title={t('dashboard.title')} subtitle={t('dashboard.subtitle')} />

      <div className="grid gap-4 xl:grid-cols-12">
        <WelcomePanel modules={visibleModules} className="xl:col-span-8" />
        <ActivityPanel className="xl:col-span-4" />
        {WIDGETS.map((widget) => (
          <ChartCard
            key={widget.key}
            className={widget.span}
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

function WelcomePanel({
  modules,
  className,
}: {
  modules: ModuleEntry[]
  className?: string
}) {
  const { t } = useTranslation()

  return (
    <Card className={cn('relative overflow-hidden p-6', className)}>
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-24 -right-16 size-64 rounded-full bg-brand/10 blur-3xl"
      />
      <div className="relative space-y-5">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold tracking-tight">
            {t('dashboard.welcomeTitle')}
          </h2>
          <p className="max-w-md text-sm text-muted">{t('dashboard.welcomeText')}</p>
        </div>
        <div>
          <p className="mb-2 text-xs font-semibold tracking-wider text-muted uppercase">
            {t('dashboard.quickAccess')}
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            {modules.map(({ moduleKey, to, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className="group flex items-center gap-3 rounded-md border border-border bg-surface/70 px-3 py-2.5 text-sm font-medium transition-colors hover:border-brand/40 hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
              >
                <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-brand-muted text-brand">
                  <Icon aria-hidden="true" className="size-4" />
                </span>
                <span className="flex-1 truncate">{t(`nav.${moduleKey}`)}</span>
                <ArrowRight
                  aria-hidden="true"
                  className="size-4 text-muted transition-transform group-hover:translate-x-0.5"
                />
              </Link>
            ))}
          </div>
        </div>
      </div>
    </Card>
  )
}

function ActivityPanel({ className }: { className?: string }) {
  const { t } = useTranslation()

  return (
    <Card className={cn('flex flex-col', className)}>
      <CardHeader>
        <CardTitle>{t('dashboard.activityTitle')}</CardTitle>
      </CardHeader>
      <div className="flex-1 px-5 pb-5">
        <EmptyState
          icon={History}
          title={t('dashboard.activityEmptyTitle')}
          description={t('dashboard.activityEmptyDescription')}
          className="h-full"
        />
      </div>
    </Card>
  )
}
