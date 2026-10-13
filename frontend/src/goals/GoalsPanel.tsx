// Panneau des objectifs du tableau de bord (sous-phase 6a-iv). Il liste les
// objectifs visibles avec leur progression et leur statut (calculés par le
// backend), et permet à qui a le droit d'écrire sur un module de créer,
// modifier ou supprimer un objectif. Toutes les données viennent de l'API,
// tous les libellés de l'i18n (AGENTS.md §7, §8).
import { useState } from 'react'
import { Target } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { Goal, MyPermissionsOut } from '../api/types.ts'
import { useAuth } from '../auth/context.ts'
import { Button } from '../components/ui/Button.tsx'
import { Card, CardHeader, CardTitle } from '../components/ui/Card.tsx'
import { EmptyState } from '../components/ui/EmptyState.tsx'
import { ErrorState } from '../components/ui/ErrorState.tsx'
import { Skeleton } from '../components/ui/Skeleton.tsx'
import { cn } from '../lib/utils.ts'
import {
  canEditMetric,
  formatGoalNumber,
  goalMetricMeta,
  goalMetricOptions,
  goalStatusMeta,
} from './format.ts'
import { GoalForm } from './GoalForm.tsx'
import { useDeleteGoal, useGoals } from './queries.ts'

export function GoalsPanel({ className }: { className?: string }) {
  const { t } = useTranslation()
  const { permissions, activeOrganizationId } = useAuth()
  const organizationId = activeOrganizationId ?? ''
  const goalsQuery = useGoals(organizationId)
  const metricOptions = goalMetricOptions(permissions)
  const [editing, setEditing] = useState<Goal | 'new' | null>(null)

  const goals = goalsQuery.data ?? []

  return (
    <Card className={cn('flex flex-col', className)}>
      <CardHeader className="flex items-center justify-between gap-2">
        <CardTitle>{t('goals.title')}</CardTitle>
        {metricOptions.length > 0 && editing === null ? (
          <Button size="sm" variant="secondary" onClick={() => setEditing('new')}>
            {t('goals.add')}
          </Button>
        ) : null}
      </CardHeader>
      <div className="flex-1 px-5 pb-5">
        {editing !== null ? (
          <GoalForm
            organizationId={organizationId}
            goal={editing === 'new' ? null : editing}
            metricOptions={metricOptions}
            onClose={() => setEditing(null)}
          />
        ) : goalsQuery.isPending ? (
          <GoalsSkeleton />
        ) : goalsQuery.isError ? (
          <ErrorState
            title={t('goals.loadErrorTitle')}
            description={t('goals.loadErrorDescription')}
            retryLabel={t('common.retry')}
            onRetry={() => {
              void goalsQuery.refetch()
            }}
          />
        ) : goals.length === 0 ? (
          <EmptyState
            icon={Target}
            title={t('goals.emptyTitle')}
            description={t('goals.emptyDescription')}
            className="h-full"
          />
        ) : (
          <ul role="list" aria-label={t('goals.title')} className="space-y-3">
            {goals.map((goal) => (
              <GoalRow
                key={goal.id}
                goal={goal}
                organizationId={organizationId}
                permissions={permissions}
                onEdit={() => setEditing(goal)}
              />
            ))}
          </ul>
        )}
      </div>
    </Card>
  )
}

/** Une ligne d'objectif : nom, cible, progression, statut et actions. */
function GoalRow({
  goal,
  organizationId,
  permissions,
  onEdit,
}: {
  goal: Goal
  organizationId: string
  permissions: MyPermissionsOut | null
  onEdit: () => void
}) {
  const { t, i18n } = useTranslation()
  const deleteGoal = useDeleteGoal(organizationId)
  const meta = goalMetricMeta(goal.metric_key)
  const name = goal.label ?? (meta ? t(meta.labelKey) : goal.metric_key)
  const status = goalStatusMeta(goal.progress.status)
  const progress = goal.progress.progress_percent ?? null
  const unit = meta?.unitKey ? ` ${t(meta.unitKey)}` : ''
  const target = formatGoalNumber(goal.target_value, i18n.language, meta?.decimals ?? 0)
  const directionLabel = t(
    goal.direction === 'at_least' ? 'goals.directionAtLeast' : 'goals.directionAtMost',
  )
  const periodLabel = t('dashboard.periodDays', { days: goal.period_days })
  const canEdit = canEditMetric(goal.metric_key, permissions)

  function handleDelete() {
    if (window.confirm(t('goals.deleteConfirm'))) {
      deleteGoal.mutate(goal.id)
    }
  }

  return (
    <li className="rounded-md border border-border p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-foreground">{name}</p>
          <p className="text-xs text-muted">
            {`${directionLabel} ${target}${unit} · ${periodLabel}`}
          </p>
        </div>
        <span
          className={cn(
            'inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 text-xs font-medium',
            status.badgeClassName,
          )}
        >
          {t(status.labelKey)}
        </span>
      </div>

      <div className="mt-2 space-y-1">
        {progress !== null ? (
          <div
            role="progressbar"
            aria-label={t('goals.progressAria', { name })}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(progress)}
            className="h-2 w-full overflow-hidden rounded-full bg-surface-muted"
          >
            <div
              className={cn('h-full rounded-full', status.barClassName)}
              style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
            />
          </div>
        ) : null}
        <p className="text-xs text-muted">
          {progress === null
            ? t('goals.progressUnknown')
            : t('goals.progressValue', {
                percent: formatGoalNumber(progress, i18n.language, 1),
              })}
        </p>
      </div>

      {canEdit ? (
        <div className="mt-2 flex items-center gap-1">
          <Button size="sm" variant="ghost" onClick={onEdit}>
            {t('goals.edit')}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={deleteGoal.isPending}
            onClick={handleDelete}
          >
            {t('goals.delete')}
          </Button>
        </div>
      ) : null}

      {deleteGoal.isError ? (
        <p role="alert" className="mt-2 text-xs text-danger">
          {t('goals.deleteError')}
        </p>
      ) : null}
    </li>
  )
}

/** Ossature affichée pendant le premier chargement des objectifs. */
function GoalsSkeleton() {
  return (
    <div className="space-y-3" data-testid="goals-skeleton">
      {Array.from({ length: 2 }, (_, index) => (
        <Skeleton key={index} className="h-16 w-full" />
      ))}
    </div>
  )
}
