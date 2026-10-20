// Page Web analytics (sous-phase 5b, SPEC §3/§6/§7) : le panneau web consommé
// par l'API. Quatre KPI (visiteurs, sessions, pages vues, taux de conversion)
// puis une grille de widgets — trafic, pages, appareils, pays, engagement et
// durée. Les données viennent toujours de l'API (AGENTS.md §8), les libellés de
// l'i18n, et les couleurs des tokens de thème.
import { Eye, MousePointerClick, Target, Users } from 'lucide-react'
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
import { WEB_METRIC_KEYS, useWebPanel } from '../metrics/web.ts'
import {
  formatCountry,
  formatDay,
  formatDayLong,
  formatDuration,
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

export function WebPage() {
  const { t, i18n } = useTranslation()
  const { activeOrganizationId } = useAuth()
  const panelQuery = useWebPanel(activeOrganizationId ?? '')

  if (panelQuery.isPending) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('nav.web')} />
        <WebSkeleton />
      </div>
    )
  }

  if (panelQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('nav.web')} subtitle={t('web.subtitle')} />
        <ErrorState
          title={t('errorState.title')}
          description={t('web.errorDescription')}
          retryLabel={t('common.retry')}
          onRetry={() => void panelQuery.refetch()}
        />
      </div>
    )
  }

  const { series, missing } = panelQuery.data
  const allMissing = missing.length === WEB_METRIC_KEYS.length

  if (allMissing) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('nav.web')} subtitle={t('web.subtitle')} />
        <EmptyState
          icon={Eye}
          title={t('web.emptyTitle')}
          description={t('web.emptyDescription')}
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

  const sessions = series['web.sessions']?.points ?? []
  const visitors = series['web.visitors']?.points ?? []
  const pageviews = series['web.pageviews']?.points ?? []
  const engagement = series['web.engagement_rate']?.points ?? []
  const duration = series['web.avg_session_duration']?.points ?? []
  const conversionPoints = conversionSeries(series['web.conversions']?.points ?? [], sessions)

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('nav.web')}
        subtitle={t('web.subtitle')}
        printable
        actions={
          <span className="rounded-full border border-border bg-surface-muted px-3 py-1 text-xs text-muted">
            {t('web.demoNote')}
          </span>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label={t('web.kpiVisitors')}
          value={lastValue(visitors)}
          unit={t('web.unitVisitors')}
          trend={lastValueTrend(visitors)}
          icon={Users}
        />
        <KpiCard
          label={t('web.kpiSessions')}
          value={lastValue(sessions)}
          unit={t('web.unitSessions')}
          trend={lastValueTrend(sessions)}
          icon={MousePointerClick}
        />
        <KpiCard
          label={t('web.kpiPageviews')}
          value={lastValue(pageviews)}
          unit={t('web.unitPageviews')}
          trend={lastValueTrend(pageviews)}
          icon={Eye}
        />
        <KpiCard
          label={t('web.kpiConversionRate')}
          value={(conversionPoints.at(-1)?.value ?? 0) * 100}
          unit="%"
          decimals={1}
          trend={lastValueTrend(conversionPoints)}
          icon={Target}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-12">
        <ChartCard
          className="xl:col-span-8"
          title={t('web.chartSessionsVisitors')}
          description={t('web.chartSessionsVisitorsDescription')}
          empty={sessions.length === 0 || visitors.length === 0}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        >
          <MultiSeriesChart
            data={zipTwo(sessions, visitors, 'sessions', 'visitors')}
            series={[
              { key: 'sessions', name: t('web.seriesSessions'), color: 'var(--brand)' },
              { key: 'visitors', name: t('web.seriesVisitors'), color: 'var(--success)' },
            ]}
            variant="area"
            ariaLabel={t('web.chartSessionsVisitors')}
            {...countChart}
          />
        </ChartCard>

        <DistributionCard
          className="xl:col-span-4"
          title={t('web.chartSources')}
          description={t('web.chartSourcesDescription')}
          points={series['web.traffic_sources']?.points ?? []}
          labelOf={(name) => t(`web.source.${name}`)}
          formatAmount={formatCount}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        />

        <ChartCard
          className="xl:col-span-4"
          title={t('web.chartPageviews')}
          description={t('web.chartPageviewsDescription')}
          empty={pageviews.length === 0}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        >
          <MultiSeriesChart
            data={oneSeries(pageviews, 'pageviews')}
            series={[
              { key: 'pageviews', name: t('web.seriesPageviews'), color: 'var(--brand)' },
            ]}
            variant="line"
            ariaLabel={t('web.chartPageviews')}
            {...countChart}
          />
        </ChartCard>

        <DistributionCard
          className="xl:col-span-4"
          title={t('web.chartTopPages')}
          description={t('web.chartTopPagesDescription')}
          points={series['web.top_pages']?.points ?? []}
          labelOf={(name) => name}
          formatAmount={formatCount}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        />

        <ChartCard
          className="xl:col-span-4"
          title={t('web.chartDuration')}
          description={t('web.chartDurationDescription')}
          empty={duration.length === 0}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        >
          <MultiSeriesChart
            data={oneSeries(duration, 'duration')}
            series={[
              { key: 'duration', name: t('web.seriesDuration'), color: 'var(--warning)' },
            ]}
            variant="line"
            ariaLabel={t('web.chartDuration')}
            formatValue={(value) => formatDuration(value, language)}
            formatAxis={(value) => formatDuration(value, language)}
            formatAxisLabel={(label) => formatDay(label, language)}
            labelFormatter={(label) => formatDayLong(label, language)}
          />
        </ChartCard>

        <DistributionCard
          className="xl:col-span-4"
          title={t('web.chartDevices')}
          description={t('web.chartDevicesDescription')}
          points={series['web.devices']?.points ?? []}
          labelOf={(name) => t(`web.device.${name}`)}
          formatAmount={formatCount}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        />

        <DistributionCard
          className="xl:col-span-4"
          title={t('web.chartCountries')}
          description={t('web.chartCountriesDescription')}
          points={series['web.countries']?.points ?? []}
          labelOf={(name) => formatCountry(name, language)}
          formatAmount={formatCount}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        />

        <ChartCard
          className="xl:col-span-4"
          title={t('web.chartEngagement')}
          description={t('web.chartEngagementDescription')}
          empty={engagement.length === 0}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        >
          <MultiSeriesChart
            data={oneSeries(engagement, 'engagement')}
            series={[
              { key: 'engagement', name: t('web.seriesEngagement'), color: 'var(--brand)' },
            ]}
            variant="line"
            ariaLabel={t('web.chartEngagement')}
            formatValue={(value) => formatPercent(value / 100, language)}
            formatAxis={(value) => formatPercent(value / 100, language)}
            formatAxisLabel={(label) => formatDay(label, language)}
            labelFormatter={(label) => formatDayLong(label, language)}
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

/** Taux de conversion du jour (conversions / sessions), jour par jour. */
function conversionSeries(conversions: MetricPoint[], sessions: MetricPoint[]): MetricPoint[] {
  return conversions.map((point, index) => {
    const total = sessions[index]?.value ?? 0
    return { at: point.at, value: total > 0 ? point.value / total : 0 }
  })
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
function WebSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => (
          <ChartCard key={index} title="" loading emptyTitle="" />
        ))}
      </div>
      <div className="grid gap-4 xl:grid-cols-12">
        {Array.from({ length: 9 }, (_, index) => (
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
