// Page « Vue d'ensemble » (sous-phases 5f, 6a, 6b-ii-b) : le Pouls de
// l'entreprise, présenté sous forme de widgets déplaçables. La disposition est
// personnelle et persistée par membre (sous-phase 6b-ii-a) : l'API renvoie le
// catalogue des widgets autorisés et la disposition courante, la page compose la
// grille. Toutes les données viennent de l'API (AGENTS.md §8), tous les libellés
// de l'i18n ; le backend filtre déjà par module autorisé.
import { useEffect, useState } from 'react'
import { useQueries } from '@tanstack/react-query'
import { Check, GripVertical, PenLine, RotateCcw } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { Layout, LayoutItem } from 'react-grid-layout'
import type {
  DashboardPlacement,
  DashboardWidget,
  MetricComparison,
} from '../api/types.ts'
import { useAuth } from '../auth/context.ts'
import { Button } from '../components/ui/Button.tsx'
import { Card, CardContent } from '../components/ui/Card.tsx'
import { ErrorState } from '../components/ui/ErrorState.tsx'
import { PageHeader } from '../components/ui/PageHeader.tsx'
import { PeriodSelect } from '../components/ui/PeriodSelect.tsx'
import { Skeleton } from '../components/ui/Skeleton.tsx'
import { DashboardGrid } from '../dashboard/DashboardGrid.tsx'
import { sameLayout, toGridLayout, toPlacements, widgetTitleKey } from '../dashboard/layout.ts'
import { useDashboard, useResetDashboard, useSaveDashboard } from '../dashboard/queries.ts'
import { DashboardWidgetView, EmptyDashboard, type WidgetData } from '../dashboard/widgets.tsx'
import { cn } from '../lib/utils.ts'
import {
  DEFAULT_PERIOD_DAYS,
  PERIOD_OPTIONS,
  fetchMetricComparison,
  metricsKeys,
} from '../metrics/queries.ts'
import { usePulse } from '../pulse/queries.ts'

/** Widget résolu : son entrée de catalogue, garantie présente. */
interface ResolvedWidget {
  item: LayoutItem
  widget: DashboardWidget
}

export function DashboardPage() {
  const { t } = useTranslation()
  const { activeOrganizationId } = useAuth()
  const organizationId = activeOrganizationId ?? ''
  const [periodDays, setPeriodDays] = useState<number>(DEFAULT_PERIOD_DAYS)
  const [editing, setEditing] = useState(false)

  const pulseQuery = usePulse(organizationId)
  const dashboardQuery = useDashboard(organizationId)
  const saveDashboard = useSaveDashboard(organizationId)
  const resetDashboard = useResetDashboard(organizationId)

  // Le tableau de bord compare chaque KPI clé sur la fenêtre choisie (SPEC §4,
  // phase 6a). Une requête par KPI visible : le Pouls fournit la liste autorisée,
  // la comparaison fournit l'agrégat et l'écart. Les requêtes dépendent du Pouls
  // (liste des clés), d'où les deux temps ; elles sont appelées ici, avant tout
  // retour anticipé, pour respecter l'ordre des hooks.
  const kpiKeys = (pulseQuery.data?.kpis ?? []).map((kpi) => kpi.metric_key)
  const comparisonQueries = useQueries({
    queries: kpiKeys.map((metricKey) => ({
      queryKey: metricsKeys.comparison(organizationId, metricKey, periodDays),
      queryFn: () => fetchMetricComparison(organizationId, metricKey, periodDays),
      enabled: Boolean(organizationId),
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

  // Brouillon de disposition : `null` tant que l'utilisateur n'a rien déplacé,
  // auquel cas la disposition serveur fait foi. Toute nouvelle disposition
  // serveur (chargement, enregistrement, remise à zéro) repart du brouillon vide.
  const [draft, setDraft] = useState<DashboardPlacement[] | null>(null)
  useEffect(() => {
    setDraft(null)
  }, [dashboardQuery.data])

  const serverLayout = dashboardQuery.data?.layout ?? []
  const placements = draft ?? serverLayout

  if (pulseQuery.isPending || dashboardQuery.isPending) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('dashboard.title')} subtitle={t('dashboard.subtitle')} />
        <PulseSkeleton />
      </div>
    )
  }

  if (pulseQuery.isError || dashboardQuery.isError || !dashboardQuery.data) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('dashboard.title')} subtitle={t('dashboard.subtitle')} />
        <ErrorState
          title={t('errorState.title')}
          description={t('dashboard.errorDescription')}
          retryLabel={t('common.retry')}
          onRetry={() => {
            void pulseQuery.refetch()
            void dashboardQuery.refetch()
          }}
        />
      </div>
    )
  }

  const { kpis = [], health, activity = [] } = pulseQuery.data
  const dashboard = dashboardQuery.data
  const widgetsById = new Map(dashboard.available_widgets.map((widget) => [widget.widget_id, widget]))
  const items: ResolvedWidget[] = toGridLayout(placements)
    .map((item) => ({ item, widget: widgetsById.get(item.i) }))
    .filter((entry): entry is ResolvedWidget => entry.widget !== undefined)

  const data: WidgetData = {
    kpis: new Map(kpis.map((kpi) => [kpi.metric_key, kpi])),
    comparisons,
    health,
    activity,
  }
  const hasKpi = items.some((entry) => entry.widget.kind === 'kpi')

  function handleLayoutChange(next: Layout) {
    if (sameLayout(toGridLayout(placements), next)) return
    setDraft(toPlacements(next))
  }

  function handleSave() {
    saveDashboard.mutate({ widgets: placements }, { onSuccess: () => setEditing(false) })
  }

  function handleReset() {
    resetDashboard.mutate(undefined, { onSuccess: () => setEditing(false) })
  }

  function handleCancel() {
    setDraft(null)
    setEditing(false)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('dashboard.title')}
        subtitle={t('dashboard.subtitle')}
        printable
        printPeriod={t('dashboard.periodDays', { days: periodDays })}
        actions={
          editing ? (
            <>
              <Button variant="ghost" onClick={handleCancel}>
                {t('dashboard.cancel')}
              </Button>
              <Button
                variant="secondary"
                onClick={handleReset}
                disabled={resetDashboard.isPending}
              >
                <RotateCcw aria-hidden="true" className="size-4" />
                {t('dashboard.reset')}
              </Button>
              <Button onClick={handleSave} disabled={saveDashboard.isPending}>
                <Check aria-hidden="true" className="size-4" />
                {t('dashboard.save')}
              </Button>
            </>
          ) : (
            <Button variant="secondary" onClick={() => setEditing(true)}>
              <PenLine aria-hidden="true" className="size-4" />
              {t('dashboard.customize')}
            </Button>
          )
        }
      />

      {hasKpi ? (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-medium text-muted">{t('dashboard.periodLabel')}</h2>
          <PeriodSelect
            label={t('dashboard.periodLabel')}
            value={periodDays}
            onChange={setPeriodDays}
            options={PERIOD_OPTIONS.map((days) => ({
              value: days,
              label: t('dashboard.periodDays', { days }),
            }))}
          />
        </div>
      ) : null}

      {editing ? <p className="text-sm text-muted">{t('dashboard.editHint')}</p> : null}

      {items.length === 0 ? (
        <EmptyDashboard />
      ) : (
        <DashboardGrid
          layout={toGridLayout(placements)}
          editable={editing}
          onLayoutChange={handleLayoutChange}
        >
          {items.map((entry) => (
            <div
              key={entry.item.i}
              data-widget-id={entry.item.i}
              className="flex h-full flex-col"
            >
              {editing ? (
                <div className="widget-handle mb-1 flex cursor-move items-center gap-2 rounded-md bg-surface-muted px-2 py-1 text-xs font-medium text-muted">
                  <GripVertical aria-hidden="true" className="size-3.5" />
                  <span className="truncate">{t(widgetTitleKey(entry.widget))}</span>
                </div>
              ) : null}
              <div className={cn('min-h-0', editing ? 'flex-1' : 'h-full')}>
                <DashboardWidgetView widget={entry.widget} data={data} />
              </div>
            </div>
          ))}
        </DashboardGrid>
      )}
    </div>
  )
}

/** Squelette chargé pendant la première requête du Pouls ou de la disposition. */
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
