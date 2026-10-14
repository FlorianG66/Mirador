// Page Réseaux sociaux (sous-phase 5c, SPEC §3/§6/§7) : le panneau social
// consommé par l'API. Quatre KPI (abonnés, impressions, portée, engagement)
// puis une grille de widgets — diffusion, abonnés par réseau, croissance,
// engagement, mentions, meilleurs posts, interactions et publications. Les
// données viennent toujours de l'API (AGENTS.md §8), les libellés de l'i18n,
// et les couleurs des tokens de thème.
import { Megaphone, Radar, Share2, ThumbsUp, Users } from 'lucide-react'
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
import { SOCIAL_METRIC_KEYS, useSocialPanel } from '../metrics/social.ts'
import {
  formatDay,
  formatDayLong,
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

export function SocialPage() {
  const { t, i18n } = useTranslation()
  const { activeOrganizationId } = useAuth()
  const panelQuery = useSocialPanel(activeOrganizationId ?? '')

  if (panelQuery.isPending) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('nav.social')} />
        <SocialSkeleton />
      </div>
    )
  }

  if (panelQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('nav.social')} subtitle={t('social.subtitle')} />
        <ErrorState
          title={t('errorState.title')}
          description={t('social.errorDescription')}
          retryLabel={t('common.retry')}
          onRetry={() => void panelQuery.refetch()}
        />
      </div>
    )
  }

  const { series, missing } = panelQuery.data
  const allMissing = missing.length === SOCIAL_METRIC_KEYS.length

  if (allMissing) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('nav.social')} subtitle={t('social.subtitle')} />
        <EmptyState
          icon={Share2}
          title={t('social.emptyTitle')}
          description={t('social.emptyDescription')}
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

  const followers = series['social.followers']?.points ?? []
  const growth = series['social.followers_growth']?.points ?? []
  const impressions = series['social.impressions']?.points ?? []
  const reach = series['social.reach']?.points ?? []
  const engagements = series['social.engagements']?.points ?? []
  const engagementRate = series['social.engagement_rate']?.points ?? []
  const mentions = series['social.mentions']?.points ?? []
  const posts = series['social.posts']?.points ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('nav.social')}
        subtitle={t('social.subtitle')}
        printable
        actions={
          <span className="rounded-full border border-border bg-surface-muted px-3 py-1 text-xs text-muted">
            {t('social.demoNote')}
          </span>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label={t('social.kpiFollowers')}
          value={lastValue(followers)}
          unit={t('social.unitFollowers')}
          trend={lastValueTrend(followers)}
          icon={Users}
        />
        <KpiCard
          label={t('social.kpiImpressions')}
          value={lastValue(impressions)}
          unit={t('social.unitImpressions')}
          trend={lastValueTrend(impressions)}
          icon={Megaphone}
        />
        <KpiCard
          label={t('social.kpiReach')}
          value={lastValue(reach)}
          unit={t('social.unitReach')}
          trend={lastValueTrend(reach)}
          icon={Radar}
        />
        <KpiCard
          label={t('social.kpiEngagementRate')}
          value={lastValue(engagementRate)}
          unit="%"
          decimals={1}
          trend={lastValueTrend(engagementRate)}
          icon={ThumbsUp}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-12">
        <ChartCard
          className="xl:col-span-8"
          title={t('social.chartImpressionsReach')}
          description={t('social.chartImpressionsReachDescription')}
          empty={impressions.length === 0 || reach.length === 0}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        >
          <MultiSeriesChart
            data={zipTwo(impressions, reach, 'impressions', 'reach')}
            series={[
              { key: 'impressions', name: t('social.seriesImpressions'), color: 'var(--brand)' },
              { key: 'reach', name: t('social.seriesReach'), color: 'var(--success)' },
            ]}
            variant="area"
            ariaLabel={t('social.chartImpressionsReach')}
            {...countChart}
          />
        </ChartCard>

        <DistributionCard
          className="xl:col-span-4"
          title={t('social.chartFollowersByNetwork')}
          description={t('social.chartFollowersByNetworkDescription')}
          points={series['social.followers']?.points ?? []}
          labelOf={(name) => t(`social.network.${name}`)}
          formatAmount={formatCount}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        />

        <ChartCard
          className="xl:col-span-4"
          title={t('social.chartGrowth')}
          description={t('social.chartGrowthDescription')}
          empty={growth.length === 0}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        >
          <MultiSeriesChart
            data={oneSeries(growth, 'growth')}
            series={[{ key: 'growth', name: t('social.seriesGrowth'), color: 'var(--success)' }]}
            variant="line"
            ariaLabel={t('social.chartGrowth')}
            {...countChart}
          />
        </ChartCard>

        <ChartCard
          className="xl:col-span-4"
          title={t('social.chartEngagementRate')}
          description={t('social.chartEngagementRateDescription')}
          empty={engagementRate.length === 0}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        >
          <MultiSeriesChart
            data={oneSeries(engagementRate, 'engagementRate')}
            series={[
              { key: 'engagementRate', name: t('social.seriesEngagementRate'), color: 'var(--brand)' },
            ]}
            variant="line"
            ariaLabel={t('social.chartEngagementRate')}
            formatValue={(value) => formatPercent(value / 100, language)}
            formatAxis={(value) => formatPercent(value / 100, language)}
            formatAxisLabel={(label) => formatDay(label, language)}
            labelFormatter={(label) => formatDayLong(label, language)}
          />
        </ChartCard>

        <ChartCard
          className="xl:col-span-4"
          title={t('social.chartMentions')}
          description={t('social.chartMentionsDescription')}
          empty={mentions.length === 0}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        >
          <MultiSeriesChart
            data={oneSeries(mentions, 'mentions')}
            series={[{ key: 'mentions', name: t('social.seriesMentions'), color: 'var(--warning)' }]}
            variant="line"
            ariaLabel={t('social.chartMentions')}
            {...countChart}
          />
        </ChartCard>

        <DistributionCard
          className="xl:col-span-4"
          title={t('social.chartTopPosts')}
          description={t('social.chartTopPostsDescription')}
          points={series['social.top_posts']?.points ?? []}
          labelOf={(name) => name}
          formatAmount={formatCount}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        />

        <ChartCard
          className="xl:col-span-4"
          title={t('social.chartEngagements')}
          description={t('social.chartEngagementsDescription')}
          empty={engagements.length === 0}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        >
          <MultiSeriesChart
            data={oneSeries(engagements, 'engagements')}
            series={[
              { key: 'engagements', name: t('social.seriesEngagements'), color: 'var(--brand)' },
            ]}
            variant="line"
            ariaLabel={t('social.chartEngagements')}
            {...countChart}
          />
        </ChartCard>

        <ChartCard
          className="xl:col-span-4"
          title={t('social.chartPosts')}
          description={t('social.chartPostsDescription')}
          empty={posts.length === 0}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        >
          <MultiSeriesChart
            data={oneSeries(posts, 'posts')}
            series={[{ key: 'posts', name: t('social.chartPosts'), color: 'var(--brand)' }]}
            variant="bar"
            ariaLabel={t('social.chartPosts')}
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
function SocialSkeleton() {
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
