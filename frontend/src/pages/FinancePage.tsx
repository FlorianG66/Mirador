// Page Finance (sous-phase 5a, SPEC §3/§6/§7) : le panneau financier consommée
// par l'API. Quatre KPI (CA, trésorerie, marge, impayés) puis une grille de
// graphiques — flux, budget, marge, ancienneté des impayés, tops clients et
// fournisseurs. Les données viennent toujours de l'API (AGENTS.md §8), les
// libellés de l'i18n, et les couleurs des tokens de thème.
import { Coins, Percent, ReceiptText, Wallet } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/context.ts'
import type { MetricPoint, MetricSeries } from '../api/types.ts'
import { Card, CardContent } from '../components/ui/Card.tsx'
import { ChartCard } from '../components/ui/ChartCard.tsx'
import { EmptyState } from '../components/ui/EmptyState.tsx'
import { ErrorState } from '../components/ui/ErrorState.tsx'
import { KpiCard } from '../components/ui/KpiCard.tsx'
import { PageHeader } from '../components/ui/PageHeader.tsx'
import { MultiSeriesChart, type ChartDatum } from '../components/metrics/MultiSeriesChart.tsx'
import { RankedList, type RankedItem } from '../components/metrics/RankedList.tsx'
import { Skeleton } from '../components/ui/Skeleton.tsx'
import {
  FINANCE_METRIC_KEYS,
  useFinancePanel,
} from '../metrics/finance.ts'
import { formatCurrency, formatCurrencyShort, formatDay, formatDayLong, lastPoint, lastValueTrend } from '../metrics/format.ts'

interface AgingBucket {
  days: number
  count: number
}

export function FinancePage() {
  const { t, i18n } = useTranslation()
  const { activeOrganizationId } = useAuth()
  const panelQuery = useFinancePanel(activeOrganizationId ?? '')

  if (panelQuery.isPending) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('nav.finance')} />
        <FinanceSkeleton />
      </div>
    )
  }

  if (panelQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('nav.finance')} subtitle={t('finance.subtitle')} />
        <ErrorState
          title={t('errorState.title')}
          description={t('finance.errorDescription')}
          retryLabel={t('common.retry')}
          onRetry={() => void panelQuery.refetch()}
        />
      </div>
    )
  }

  const { series, missing } = panelQuery.data
  const allMissing = missing.length === FINANCE_METRIC_KEYS.length

  if (allMissing) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('nav.finance')} subtitle={t('finance.subtitle')} />
        <EmptyState
          icon={Wallet}
          title={t('finance.emptyTitle')}
          description={t('finance.emptyDescription')}
        />
      </div>
    )
  }

  const language = i18n.language
  const chartProps = {
    formatValue: (value: number) => formatCurrency(value, language),
    formatAxis: (value: number) => formatCurrencyShort(value, language),
    formatAxisLabel: (label: string) => formatDay(label, language),
    labelFormatter: (label: string) => formatDayLong(label, language),
  }

  const revenue = series['finance.revenue']?.points ?? []
  const expenses = series['finance.expenses']?.points ?? []
  const margin = series['finance.margin']?.points ?? []
  const cash = series['finance.cash']?.points ?? []
  const budget = series['finance.budget']?.points ?? []
  const invoices = series['finance.invoices_outstanding']?.points ?? []

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('nav.finance')}
        subtitle={t('finance.subtitle')}
        printable
        actions={
          <span className="rounded-full border border-border bg-surface-muted px-3 py-1 text-xs text-muted">
            {t('finance.demoNote')}
          </span>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label={t('finance.kpiRevenue')}
          value={lastValue(revenue)}
          unit={t('common.currencyEur')}
          trend={lastValueTrend(revenue)}
          icon={Wallet}
        />
        <KpiCard
          label={t('finance.kpiCash')}
          value={lastValue(cash)}
          unit={t('common.currencyEur')}
          trend={lastValueTrend(cash)}
          icon={Coins}
        />
        <KpiCard
          label={t('finance.kpiMargin')}
          value={lastValue(margin)}
          unit={t('common.currencyEur')}
          trend={lastValueTrend(margin)}
          icon={Percent}
        />
        <KpiCard
          label={t('finance.kpiInvoicesOutstanding')}
          value={lastValue(invoices)}
          unit={t('finance.unitInvoices')}
          trend={lastValueTrend(invoices)}
          icon={ReceiptText}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-12">
        <ChartCard
          className="xl:col-span-8"
          title={t('finance.chartRevenueExpenses')}
          description={t('finance.chartRevenueExpensesDescription')}
          empty={revenue.length === 0 || expenses.length === 0}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        >
          <MultiSeriesChart
            data={zipTwo(revenue, expenses, 'revenue', 'expenses')}
            series={[
              { key: 'revenue', name: t('finance.seriesRevenue'), color: 'var(--brand)' },
              { key: 'expenses', name: t('finance.seriesExpenses'), color: 'var(--danger)' },
            ]}
            variant="area"
            ariaLabel={t('finance.chartRevenueExpenses')}
            {...chartProps}
          />
        </ChartCard>

        <ChartCard
          className="xl:col-span-4"
          title={t('finance.chartInvoicesAging')}
          description={t('finance.chartInvoicesAgingDescription')}
          empty={invoices.length === 0}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        >
          <AgingBreakdown series={invoices} />
        </ChartCard>

        <ChartCard
          className="xl:col-span-6"
          title={t('finance.chartBudget')}
          description={t('finance.chartBudgetDescription')}
          empty={budget.length === 0 || revenue.length === 0}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        >
          <MultiSeriesChart
            data={zipTwo(budget, revenue, 'budget', 'realized')}
            series={[
              { key: 'budget', name: t('finance.seriesBudget'), color: 'var(--warning)' },
              { key: 'realized', name: t('finance.seriesRealized'), color: 'var(--brand)' },
            ]}
            variant="bar"
            ariaLabel={t('finance.chartBudget')}
            {...chartProps}
          />
        </ChartCard>

        <ChartCard
          className="xl:col-span-6"
          title={t('finance.chartMargin')}
          description={t('finance.chartMarginDescription')}
          empty={margin.length === 0}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        >
          <MultiSeriesChart
            data={oneSeries(margin, 'margin')}
            series={[{ key: 'margin', name: t('finance.seriesMargin'), color: 'var(--success)' }]}
            variant="line"
            ariaLabel={t('finance.chartMargin')}
            {...chartProps}
          />
        </ChartCard>

        <TopCard
          className="xl:col-span-6"
          title={t('finance.chartTopClients')}
          description={t('finance.chartTopClientsDescription')}
          series={series['finance.top_clients']}
          language={language}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        />

        <TopCard
          className="xl:col-span-6"
          title={t('finance.chartTopSuppliers')}
          description={t('finance.chartTopSuppliersDescription')}
          series={series['finance.top_suppliers']}
          language={language}
          emptyTitle={t('emptyState.title')}
          emptyDescription={t('emptyState.description')}
        />
      </div>
    </div>
  )
}

/** Dernière valeur d'une série, ou 0 tant qu'elle est vide (état de chargement
 * impossible ici : la page gère isPending plus haut). */
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

/** Ancienneté des factures impayées : dimensions `aging` du dernier point. */
function AgingBreakdown({ series }: { series: MetricPoint[] }) {
  const { t } = useTranslation()
  const buckets = lastValueDim<AgingBucket[]>(series, 'aging') ?? []
  const total = buckets.reduce((sum, bucket) => sum + bucket.count, 0)

  if (total <= 0) return null

  return (
    <ul role="list" aria-label={t('finance.chartInvoicesAging')} className="space-y-2">
      {buckets.map((bucket) => {
        const label =
          bucket.days <= 30
            ? t('finance.aging30')
            : bucket.days <= 60
              ? t('finance.aging60')
              : t('finance.aging90')
        const share = (bucket.count / total) * 100
        return (
          <li key={bucket.days} className="flex items-center gap-3">
            <span className="w-16 shrink-0 text-sm text-muted">{label}</span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-muted">
              <div className="h-full rounded-full bg-danger/70" style={{ width: `${share}%` }} />
            </div>
            <span className="w-10 shrink-0 text-right text-sm font-semibold tabular-nums">
              {bucket.count}
            </span>
          </li>
        )
      })}
    </ul>
  )
}

/** Widget des classements (clients, fournisseurs) construit sur les dimensions. */
function TopCard({
  title,
  description,
  series,
  language,
  emptyTitle,
  emptyDescription,
  className,
}: {
  title: string
  description: string
  series: MetricSeries | undefined
  language: string
  emptyTitle: string
  emptyDescription: string
  className?: string
}) {
  const items: RankedItem[] = lastValueDim(series?.points ?? [], 'top') ?? []
  const empty = items.length === 0

  return (
    <ChartCard
      className={className}
      title={title}
      description={description}
      empty={empty}
      emptyTitle={emptyTitle}
      emptyDescription={emptyDescription}
    >
      <RankedList
        items={items}
        summary={title}
        formatAmount={(value) => formatCurrency(value, language)}
      />
    </ChartCard>
  )
}

/** Dimension d'un libellé donné sur le dernier point d'une série. */
function lastValueDim<T>(points: MetricPoint[], dimension: string): T | null | undefined {
  const point = lastPoint(points)
  if (point === undefined || point.dimensions === undefined) return undefined
  return point.dimensions[dimension] as T
}

/** Squellette chargé pendant la première requête du panneau. */
function FinanceSkeleton() {
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
        {Array.from({ length: 6 }, (_, index) => (
          <ChartCard
            key={index}
            className={index < 2 ? 'xl:col-span-6' : 'xl:col-span-4'}
            title=""
            loading
            emptyTitle=""
          />
        ))}
      </div>
    </div>
  )
}
