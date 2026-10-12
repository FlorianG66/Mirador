// Page Projets & tâches (sous-phase 5d, SPEC §3/§6/§7) : le panneau projets
// consommé par l'API. Quatre KPI (tâches terminées, tâches ouvertes, avancement
// moyen, délai moyen de livraison) puis une grille de widgets — rythme
// créées/terminées, tâches par statut, retards, charge par personne, avancement,
// délai de livraison, jalons à venir et projets actifs. Les données viennent
// toujours de l'API (AGENTS.md §8), les libellés de l'i18n, et les couleurs des
// tokens de thème.
import { CheckCircle2, ClipboardList, Gauge, ListTodo, Timer } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/context.ts'
import type { MetricPoint } from '../api/types.ts'
import { ChartCard } from '../components/ui/ChartCard.tsx'
import { EmptyState } from '../components/ui/EmptyState.tsx'
import { ErrorState } from '../components/ui/ErrorState.tsx'
import { KpiCard } from '../components/ui/KpiCard.tsx'
import { PageHeader } from '../components/ui/PageHeader.tsx'
import { MultiSeriesChart, type ChartDatum } from '../components/metrics/MultiSeriesChart.tsx'
import { RankedList, type RankedItem } from '../components/metrics/RankedList.tsx'
import { PROJECT_METRIC_KEYS, useProjectsPanel } from '../metrics/projects.ts'
import {
  formatDay,
  formatDayLong,
  formatDays,
  formatInteger,
  formatPercent,
  lastPoint,
  lastValueTrend,
} from '../metrics/format.ts'

/** Une entrée de répartition telle que stockée dans les dimensions du point. */
interface DistributionItem {
  name: string
  value: number
}

export function ProjectsPage() {
  const { t, i18n } = useTranslation()
  const { activeOrganizationId } = useAuth()
  const panelQuery = useProjectsPanel(activeOrganizationId ?? '')

  if (panelQuery.isPending) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('nav.projects')} />
        <ProjectsSkeleton />
      </div>
    )
  }

  if (panelQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('nav.projects')} subtitle={t('projects.subtitle')} />
        <ErrorState
          title={t('errorState.title')}
          description={t('projects.errorDescription')}
          retryLabel={t('common.retry')}
          onRetry={() => void panelQuery.refetch()}
        />
      </div>
    )
  }

  const { series, missing } = panelQuery.data
  const allMissing = missing.length === PROJECT_METRIC_KEYS.length

  if (allMissing) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('nav.projects')} subtitle={t('projects.subtitle')} />
        <EmptyState
          icon={ClipboardList}
          title={t('projects.emptyTitle')}
          description={t('projects.emptyDescription')}
        />
      </div>
    )
  }

  const language = i18n.language
  const formatCount = (value: number) => formatInteger(value, language)
  const countChart = {
    formatValue: formatCount,
    formatAxis: formatCount,
    formatAxisLabel: (label: string) => formatDay(label, language),
    labelFormatter: (label: string) => formatDayLong(label, language),
  }
  const durationChart = {
    formatValue: (value: number) => formatDays(value, language),
    formatAxis: (value: number) => formatDays(value, language),
    formatAxisLabel: (label: string) => formatDay(label, language),
    labelFormatter: (label: string) => formatDayLong(label, language),
  }

  const done = series['projects.tasks_done']?.points ?? []
  const created = series['projects.tasks_created']?.points ?? []
  const open = series['projects.open_tasks']?.points ?? []
  const overdue = series['projects.overdue_tasks']?.points ?? []
  const completion = series['projects.avg_completion_time']?.points ?? []
  const progress = series['projects.avg_progress']?.points ?? []
  const active = series['projects.active_projects']?.points ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('nav.projects')}
        subtitle={t('projects.subtitle')}
        actions={
          <span className="rounded-full border border-border bg-surface-muted px-3 py-1 text-xs text-muted">
            {t('projects.demoNote')}
          </span>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label={t('projects.kpiTasksDone')}
          value={lastValue(done)}
          unit={t('projects.unitTasks')}
          trend={lastValueTrend(done)}
          icon={CheckCircle2}
        />
        <KpiCard
          label={t('projects.kpiOpenTasks')}
          value={lastValue(open)}
          unit={t('projects.unitTasks')}
          trend={lastValueTrend(open)}
          icon={ListTodo}
        />
        <KpiCard
          label={t('projects.kpiAvgProgress')}
          value={lastValue(progress)}
          unit="%"
          decimals={1}
          trend={lastValueTrend(progress)}
          icon={Gauge}
        />
        <KpiCard
          label={t('projects.kpiAvgCompletionTime')}
          value={lastValue(completion)}
          unit={t('projects.unitDays')}
          decimals={1}
          trend={lastValueTrend(completion)}
          icon={Timer}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-12">
        <ChartCard
          className="xl:col-span-8"
          title={t('projects.chartCreatedDone')}
          description={t('projects.chartCreatedDoneDescription')}
          empty={created.length === 0 || done.length === 0}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        >
          <MultiSeriesChart
            data={zipTwo(created, done, 'created', 'done')}
            series={[
              { key: 'created', name: t('projects.seriesCreated'), color: 'var(--brand)' },
              { key: 'done', name: t('projects.seriesDone'), color: 'var(--success)' },
            ]}
            variant="area"
            ariaLabel={t('projects.chartCreatedDone')}
            {...countChart}
          />
        </ChartCard>

        <DistributionCard
          className="xl:col-span-4"
          title={t('projects.chartTasksByStatus')}
          description={t('projects.chartTasksByStatusDescription')}
          points={series['projects.tasks_by_status']?.points ?? []}
          labelOf={(name) => t(`projects.status.${name}`)}
          formatAmount={formatCount}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        />

        <ChartCard
          className="xl:col-span-4"
          title={t('projects.chartOverdue')}
          description={t('projects.chartOverdueDescription')}
          empty={overdue.length === 0}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        >
          <MultiSeriesChart
            data={oneSeries(overdue, 'overdue')}
            series={[
              { key: 'overdue', name: t('projects.seriesOverdue'), color: 'var(--warning)' },
            ]}
            variant="line"
            ariaLabel={t('projects.chartOverdue')}
            {...countChart}
          />
        </ChartCard>

        <DistributionCard
          className="xl:col-span-4"
          title={t('projects.chartPersonLoad')}
          description={t('projects.chartPersonLoadDescription')}
          points={series['projects.person_load']?.points ?? []}
          labelOf={(name) => name}
          formatAmount={formatCount}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        />

        <ChartCard
          className="xl:col-span-4"
          title={t('projects.chartProgress')}
          description={t('projects.chartProgressDescription')}
          empty={progress.length === 0}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        >
          <MultiSeriesChart
            data={oneSeries(progress, 'progress')}
            series={[
              { key: 'progress', name: t('projects.seriesProgress'), color: 'var(--brand)' },
            ]}
            variant="line"
            ariaLabel={t('projects.chartProgress')}
            formatValue={(value) => formatPercent(value / 100, language)}
            formatAxis={(value) => formatPercent(value / 100, language)}
            formatAxisLabel={(label) => formatDay(label, language)}
            labelFormatter={(label) => formatDayLong(label, language)}
          />
        </ChartCard>

        <ChartCard
          className="xl:col-span-4"
          title={t('projects.chartCompletionTime')}
          description={t('projects.chartCompletionTimeDescription')}
          empty={completion.length === 0}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        >
          <MultiSeriesChart
            data={oneSeries(completion, 'completion')}
            series={[
              {
                key: 'completion',
                name: t('projects.seriesCompletionTime'),
                color: 'var(--success)',
              },
            ]}
            variant="line"
            ariaLabel={t('projects.chartCompletionTime')}
            {...durationChart}
          />
        </ChartCard>

        <DistributionCard
          className="xl:col-span-4"
          title={t('projects.chartMilestones')}
          description={t('projects.chartMilestonesDescription')}
          points={series['projects.upcoming_milestones']?.points ?? []}
          labelOf={(name) => name}
          formatAmount={(value) => formatDays(value, language)}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        />

        <ChartCard
          className="xl:col-span-4"
          title={t('projects.chartActiveProjects')}
          description={t('projects.chartActiveProjectsDescription')}
          empty={active.length === 0}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        >
          <MultiSeriesChart
            data={oneSeries(active, 'active')}
            series={[
              {
                key: 'active',
                name: t('projects.seriesActiveProjects'),
                color: 'var(--brand)',
              },
            ]}
            variant="line"
            ariaLabel={t('projects.chartActiveProjects')}
            {...countChart}
          />
        </ChartCard>
      </div>
    </div>
  )
}

/** Dernière valeur d'une série (état de chargement traité plus haut). */
function lastValue(points: MetricPoint[]): number {
  return lastPoint(points)?.value ?? 0
}

/** Fusionne deux séries alignées par index en un tableau de graphique. */
function zipTwo(
  left: MetricPoint[],
  right: MetricPoint[],
  leftKey: string,
  rightKey: string,
): ChartDatum[] {
  return left.map((point, index) => ({
    label: point.at,
    [leftKey]: point.value,
    [rightKey]: right[index]?.value ?? 0,
  }))
}

/** Série simple (un seul champ de valeur) en tableau de graphique. */
function oneSeries(points: MetricPoint[], key: string): ChartDatum[] {
  return points.map((point) => ({ label: point.at, [key]: point.value }))
}

/** Widget de répartition : un classement construit sur les dimensions du point. */
function DistributionCard({
  title,
  description,
  points,
  labelOf,
  formatAmount,
  emptyTitle,
  emptyDescription,
  className,
}: {
  title: string
  description: string
  points: MetricPoint[]
  labelOf: (name: string) => string
  formatAmount: (value: number) => string
  emptyTitle: string
  emptyDescription: string
  className?: string
}) {
  const items: RankedItem[] = distributionItems(points).map((item) => ({
    name: labelOf(item.name),
    amount: item.value,
  }))

  return (
    <ChartCard
      className={className}
      title={title}
      description={description}
      empty={items.length === 0}
      emptyTitle={emptyTitle}
      emptyDescription={emptyDescription}
    >
      <RankedList items={items} summary={title} formatAmount={formatAmount} />
    </ChartCard>
  )
}

/** Répartition du dernier point d'une série (dimension `items`). */
function distributionItems(points: MetricPoint[]): DistributionItem[] {
  const point = lastPoint(points)
  if (point === undefined) return []
  return (point.dimensions?.items as DistributionItem[] | undefined) ?? []
}

/** Squelette chargé pendant la première requête du panneau. */
function ProjectsSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => (
          <ChartCard key={index} title="" loading emptyTitle="" />
        ))}
      </div>
      <div className="grid gap-4 xl:grid-cols-12">
        {Array.from({ length: 8 }, (_, index) => (
          <ChartCard
            key={index}
            className={index === 0 ? 'xl:col-span-8' : 'xl:col-span-4'}
            title=""
            loading
            emptyTitle=""
          />
        ))}
      </div>
    </div>
  )
}
