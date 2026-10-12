// Page « Vue d'ensemble » (sous-phase 5f) : le Pouls de l'entreprise. Elle
// regroupe les KPI clés des modules autorisés, un indicateur de santé
// d'exploitation, le fil d'activité (réservé aux admins) et un emplacement
// d'objectifs. Toutes les données viennent de l'API (AGENTS.md §8), tous les
// libellés de l'i18n ; le backend filtre déjà par module autorisé.
import { useState } from 'react'
import { useQueries } from '@tanstack/react-query'
import type { LucideIcon } from 'lucide-react'
import {
  BarChart3,
  CircleCheck,
  CircleHelp,
  History,
  Landmark,
  ListChecks,
  Share2,
  Target,
  TriangleAlert,
  Wallet,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { AuditLog, MetricComparison, ModuleKey, PulseHealth, PulseKpi } from '../api/types.ts'
import { useAuth } from '../auth/context.ts'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card.tsx'
import { EmptyState } from '../components/ui/EmptyState.tsx'
import { ErrorState } from '../components/ui/ErrorState.tsx'
import { KpiCard } from '../components/ui/KpiCard.tsx'
import { PageHeader } from '../components/ui/PageHeader.tsx'
import { PeriodSelect } from '../components/ui/PeriodSelect.tsx'
import { Skeleton } from '../components/ui/Skeleton.tsx'
import { cn } from '../lib/utils.ts'
import {
  DEFAULT_PERIOD_DAYS,
  PERIOD_OPTIONS,
  fetchMetricComparison,
  metricsKeys,
} from '../metrics/queries.ts'
import { KPI_META, actionLabelKey, formatRelativeTime, kpiTrend } from '../pulse/format.ts'
import { usePulse } from '../pulse/queries.ts'

// Icône d'un module pour les KPI (réutilise celles de la navigation).
const MODULE_ICONS: Record<ModuleKey, LucideIcon> = {
  finance: Wallet,
  web: BarChart3,
  social: Share2,
  projects: ListChecks,
  legal: Landmark,
}

export function DashboardPage() {
  const { t } = useTranslation()
  const { permissions, activeOrganizationId } = useAuth()
  const [periodDays, setPeriodDays] = useState<number>(DEFAULT_PERIOD_DAYS)
  const pulseQuery = usePulse(activeOrganizationId ?? '')

  // Le tableau de bord compare chaque KPI clé sur la fenêtre choisie (SPEC §4,
  // phase 6a). Une requête par KPI visible : le Pouls fournit la liste autorisée,
  // la comparaison fournit l'agrégat et l'écart. Les requêtes dépendent du Pouls
  // (liste des clés), d'où les deux temps ; elles sont appelées ici, avant tout
  // retour anticipé, pour respecter l'ordre des hooks.
  const kpiKeys = (pulseQuery.data?.kpis ?? []).map((kpi) => kpi.metric_key)
  const comparisonQueries = useQueries({
    queries: kpiKeys.map((metricKey) => ({
      queryKey: metricsKeys.comparison(activeOrganizationId ?? '', metricKey, periodDays),
      queryFn: () =>
        fetchMetricComparison(activeOrganizationId ?? '', metricKey, periodDays),
      enabled: Boolean(activeOrganizationId),
      retry: false,
      refetchOnWindowFocus: false,
    })),
  })
  const comparisons = new Map<string, MetricComparison>()
  comparisonQueries.forEach((query, index) => {
    if (query.data) {
      comparisons.set(kpiKeys[index], query.data)
    }
  })

  if (pulseQuery.isPending) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('dashboard.title')} subtitle={t('dashboard.subtitle')} />
        <PulseSkeleton />
      </div>
    )
  }

  if (pulseQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('dashboard.title')} subtitle={t('dashboard.subtitle')} />
        <ErrorState
          title={t('errorState.title')}
          description={t('dashboard.errorDescription')}
          retryLabel={t('common.retry')}
          onRetry={() => void pulseQuery.refetch()}
        />
      </div>
    )
  }

  const { kpis = [], health, activity = [] } = pulseQuery.data
  const isAdmin = permissions?.role === 'admin'

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('dashboard.title')}
        subtitle={t('dashboard.subtitle')}
        actions={<HealthBadge health={health} />}
      />

      <KpiSection
        kpis={kpis}
        comparisons={comparisons}
        periodDays={periodDays}
        onPeriodChange={setPeriodDays}
      />

      <div className="grid gap-4 xl:grid-cols-12">
        <ActivityPanel entries={activity} isAdmin={isAdmin} className="xl:col-span-7" />
        <GoalsPanel className="xl:col-span-5" />
      </div>
    </div>
  )
}

/** Indicateur de santé d'exploitation : modules alimentés sur modules visibles. */
function HealthBadge({ health }: { health: PulseHealth }) {
  const { t } = useTranslation()
  const config: Record<PulseHealth['status'], { icon: LucideIcon; className: string }> = {
    good: { icon: CircleCheck, className: 'border-success/30 bg-success/5 text-success' },
    warning: { icon: TriangleAlert, className: 'border-warning/30 bg-warning/5 text-warning' },
    unknown: { icon: CircleHelp, className: 'border-border bg-surface-muted text-muted' },
  }
  const { icon: Icon, className } = config[health.status]
  const label = {
    good: t('dashboard.healthGood'),
    warning: t('dashboard.healthWarning', {
      withData: health.modules_with_data,
      total: health.modules_total,
    }),
    unknown: t('dashboard.healthUnknown'),
  }[health.status]

  return (
    <span
      role="status"
      aria-label={t('dashboard.healthAria')}
      className={cn(
        'inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium',
        className,
      )}
    >
      <Icon aria-hidden="true" className="size-3.5" />
      {label}
    </span>
  )
}

/**
 * Bloc des KPI clés : sélecteur de période (masqué sans donnée) puis grille. Le
 * sélecteur ne pilote que l'affichage : le backend filtre déjà par droits.
 */
function KpiSection({
  kpis,
  comparisons,
  periodDays,
  onPeriodChange,
}: {
  kpis: PulseKpi[]
  comparisons: Map<string, MetricComparison>
  periodDays: number
  onPeriodChange: (days: number) => void
}) {
  const { t } = useTranslation()

  return (
    <div className="space-y-3">
      {kpis.length > 0 ? (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-medium text-muted">{t('dashboard.periodLabel')}</h2>
          <PeriodSelect
            label={t('dashboard.periodLabel')}
            value={periodDays}
            onChange={onPeriodChange}
            options={PERIOD_OPTIONS.map((days) => ({
              value: days,
              label: t('dashboard.periodDays', { days }),
            }))}
          />
        </div>
      ) : null}
      <KpiGrid kpis={kpis} comparisons={comparisons} />
    </div>
  )
}

/** Grille des KPI clés autorisés, ou état vide si aucun module n'a de donnée. */
function KpiGrid({
  kpis,
  comparisons,
}: {
  kpis: PulseKpi[]
  comparisons: Map<string, MetricComparison>
}) {
  const { t } = useTranslation()

  if (kpis.length === 0) {
    return (
      <Card>
        <CardContent className="p-5">
          <EmptyState
            icon={BarChart3}
            title={t('dashboard.kpiEmptyTitle')}
            description={t('dashboard.kpiEmptyDescription')}
          />
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {kpis.map((kpi) => {
        const meta = KPI_META[kpi.metric_key]
        // La comparaison de périodes prime sur la tendance à deux points du Pouls ;
        // sans donnée sur la fenêtre (404), on retombe sur la dernière valeur connue.
        const summary = comparisons.get(kpi.metric_key)?.summary
        return (
          <KpiCard
            key={kpi.metric_key}
            label={meta ? t(meta.labelKey) : kpi.metric_key}
            value={summary ? summary.current_value : kpi.value}
            unit={meta?.unitKey ? t(meta.unitKey) : undefined}
            decimals={meta?.decimals ?? 0}
            trend={summary ? (summary.change_percent ?? undefined) : kpiTrend(kpi)}
            icon={MODULE_ICONS[kpi.module]}
          />
        )
      })}
    </div>
  )
}

/** Fil d'activité : journal lisible par les admins, note explicite sinon. */
function ActivityPanel({
  entries,
  isAdmin,
  className,
}: {
  entries: AuditLog[]
  isAdmin: boolean
  className?: string
}) {
  const { t, i18n } = useTranslation()

  return (
    <Card className={cn('flex flex-col', className)}>
      <CardHeader>
        <CardTitle>{t('dashboard.activityTitle')}</CardTitle>
      </CardHeader>
      <div className="flex-1 px-5 pb-5">
        {!isAdmin ? (
          <EmptyState
            icon={History}
            title={t('dashboard.activityAdminOnlyTitle')}
            description={t('dashboard.activityAdminOnlyDescription')}
            className="h-full"
          />
        ) : entries.length === 0 ? (
          <EmptyState
            icon={History}
            title={t('dashboard.activityEmptyTitle')}
            description={t('dashboard.activityEmptyDescription')}
            className="h-full"
          />
        ) : (
          <ul role="list" aria-label={t('dashboard.activityTitle')} className="space-y-1">
            {entries.map((entry) => (
              <li
                key={entry.id}
                className="flex items-start gap-3 rounded-md px-2 py-2 hover:bg-surface-hover"
              >
                <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-brand-muted text-brand">
                  <History aria-hidden="true" className="size-3.5" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm">{t(actionLabelKey(entry))}</p>
                  <time dateTime={entry.created_at} className="text-xs text-muted">
                    {formatRelativeTime(entry.created_at, i18n.language)}
                  </time>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  )
}

/** Emplacement des objectifs : état vide, l'édition arrive en phase 6. */
function GoalsPanel({ className }: { className?: string }) {
  const { t } = useTranslation()

  return (
    <Card className={cn('flex flex-col', className)}>
      <CardHeader>
        <CardTitle>{t('dashboard.goalsTitle')}</CardTitle>
      </CardHeader>
      <div className="flex-1 px-5 pb-5">
        <EmptyState
          icon={Target}
          title={t('dashboard.goalsEmptyTitle')}
          description={t('dashboard.goalsEmptyDescription')}
          className="h-full"
        />
      </div>
    </Card>
  )
}

/** Squellette chargé pendant la première requête du Pouls. */
function PulseSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => (
          <Card key={index}>
            <CardContent className="space-y-3 p-5">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-8 w-32" />
            </CardContent>
          </Card>
        ))}
      </div>
      <div className="grid gap-4 xl:grid-cols-12">
        <Card className="xl:col-span-7">
          <CardContent className="p-5">
            <Skeleton className="h-48 w-full" />
          </CardContent>
        </Card>
        <Card className="xl:col-span-5">
          <CardContent className="p-5">
            <Skeleton className="h-48 w-full" />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
