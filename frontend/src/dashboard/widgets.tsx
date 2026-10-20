// Catalogue d'affichage des widgets du tableau de bord (sous-phase 6b-ii-b).
// Chaque genre de widget (santé, KPI clé, objectifs, activité) a son composant ;
// la page choisit le rendu à partir du catalogue renvoyé par l'API. Toutes les
// données viennent de l'API, tous les libellés de l'i18n (AGENTS.md §7, §8).
import type { LucideIcon } from 'lucide-react'
import {
  BarChart3,
  CircleCheck,
  CircleHelp,
  History,
  Landmark,
  ListChecks,
  Share2,
  TriangleAlert,
  Wallet,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type {
  AuditLog,
  DashboardWidget,
  MetricComparison,
  ModuleKey,
  PulseHealth,
  PulseKpi,
} from '../api/types.ts'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card.tsx'
import { EmptyState } from '../components/ui/EmptyState.tsx'
import { KpiCard } from '../components/ui/KpiCard.tsx'
import { GoalsPanel } from '../goals/GoalsPanel.tsx'
import { KPI_META, actionLabelKey, formatRelativeTime, kpiTrend } from '../pulse/format.ts'

// Icône d'un module pour les KPI (réutilise celles de la navigation).
const MODULE_ICONS: Record<ModuleKey, LucideIcon> = {
  finance: Wallet,
  web: BarChart3,
  social: Share2,
  projects: ListChecks,
  legal: Landmark,
}

/** Données partagées par les widgets, assemblées une fois par la page. */
export interface WidgetData {
  /** Dernier point du Pouls par clé de métrique. */
  kpis: Map<string, PulseKpi>
  /** Comparaison de périodes par clé de métrique (peut être vide). */
  comparisons: Map<string, MetricComparison>
  health: PulseHealth
  activity: AuditLog[]
}

/** Rend un widget selon son genre. Retourne `null` si l'entrée est inconnue. */
export function DashboardWidgetView({
  widget,
  data,
}: {
  widget: DashboardWidget
  data: WidgetData
}) {
  switch (widget.kind) {
    case 'health':
      return <HealthWidget health={data.health} />
    case 'goals':
      return <GoalsPanel className="h-full" />
    case 'activity':
      return <ActivityWidget entries={data.activity} className="h-full" />
    case 'kpi':
      return widget.metric_key ? <KpiWidget widget={widget} data={data} /> : null
    default:
      return null
  }
}

/** Indicateur de santé d'exploitation : modules alimentés sur modules visibles. */
function HealthWidget({ health }: { health: PulseHealth }) {
  const { t } = useTranslation()

  return (
    <Card className="flex h-full flex-col justify-center gap-3 p-5">
      <h2 className="text-sm font-medium text-muted">{t('dashboard.healthTitle')}</h2>
      <HealthBadge health={health} />
    </Card>
  )
}

/** Pastille colorée de santé, réutilisée par le widget de santé. */
export function HealthBadge({ health }: { health: PulseHealth }) {
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
      className={`inline-flex w-fit items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${className}`}
    >
      <Icon aria-hidden="true" className="size-3.5" />
      {label}
    </span>
  )
}

/**
 * Carte d'un KPI clé. La comparaison de périodes prime sur la tendance à deux
 * points du Pouls ; sans donnée sur la fenêtre (404), on retombe sur la dernière
 * valeur connue. Un KPI autorisé sans aucune donnée affiche un état neutre.
 */
function KpiWidget({ widget, data }: { widget: DashboardWidget; data: WidgetData }) {
  const { t } = useTranslation()
  const metricKey = widget.metric_key ?? ''
  const meta = KPI_META[metricKey]
  const label = meta ? t(meta.labelKey) : metricKey
  const kpi = data.kpis.get(metricKey)
  const summary = data.comparisons.get(metricKey)?.summary

  if (!kpi && !summary) {
    return (
      <Card className="flex h-full flex-col justify-center p-5">
        <p className="text-sm text-muted">{label}</p>
        <p className="text-2xl font-semibold tracking-tight text-muted">
          {t('dashboard.kpiNoData')}
        </p>
      </Card>
    )
  }

  return (
    <KpiCard
      className="h-full"
      label={label}
      value={summary ? summary.current_value : (kpi?.value ?? 0)}
      unit={meta?.unitKey ? t(meta.unitKey) : undefined}
      decimals={meta?.decimals ?? 0}
      trend={summary ? (summary.change_percent ?? undefined) : kpi ? kpiTrend(kpi) : undefined}
      icon={widget.module ? MODULE_ICONS[widget.module] : undefined}
    />
  )
}

/**
 * Fil d'activité : journal des actions sensibles de l'organisation. Le backend
 * ne le propose qu'aux administrateurs (catalogue + filtrage à la lecture), la
 * page ne reçoit donc jamais ce widget pour un membre.
 */
function ActivityWidget({
  entries,
  className,
}: {
  entries: AuditLog[]
  className?: string
}) {
  const { t, i18n } = useTranslation()

  return (
    <Card className={`flex flex-col ${className ?? ''}`}>
      <CardHeader>
        <CardTitle>{t('dashboard.activityTitle')}</CardTitle>
      </CardHeader>
      <div className="min-h-0 flex-1 overflow-auto px-5 pb-5">
        {entries.length === 0 ? (
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

/** État affiché quand la disposition ne contient aucun widget rendable. */
export function EmptyDashboard() {
  const { t } = useTranslation()
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
