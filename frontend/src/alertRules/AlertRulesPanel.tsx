// Panneau des règles d'alerte (sous-phase 6c-iii), affiché dans les paramètres.
// Il liste les règles visibles avec leur seuil et permet à qui a le droit
// d'écrire sur un module de créer, modifier, activer/désactiver ou supprimer une
// règle. Toutes les données viennent de l'API, tous les libellés de l'i18n
// (AGENTS.md §7, §8).
import { useState } from 'react'
import { BellRing } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { AlertRule } from '../api/types.ts'
import { useAuth } from '../auth/context.ts'
import { Button } from '../components/ui/Button.tsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card.tsx'
import { EmptyState } from '../components/ui/EmptyState.tsx'
import { ErrorState } from '../components/ui/ErrorState.tsx'
import { Skeleton } from '../components/ui/Skeleton.tsx'
import { formatGoalNumber, goalMetricMeta } from '../goals/format.ts'
import { cn } from '../lib/utils.ts'
import { AlertRuleForm } from './AlertRuleForm.tsx'
import { alertComparisonKey, alertMetricOptions, alertRuleName, canEditRule } from './format.ts'
import { useAlertRules, useDeleteAlertRule, useUpdateAlertRule } from './queries.ts'

export function AlertRulesPanel() {
  const { t } = useTranslation()
  const { permissions, activeOrganizationId } = useAuth()
  const organizationId = activeOrganizationId ?? ''
  const rulesQuery = useAlertRules(organizationId)
  const metricOptions = alertMetricOptions(permissions)
  const [editing, setEditing] = useState<AlertRule | 'new' | null>(null)

  const rules = rulesQuery.data ?? []

  return (
    <Card className="max-w-2xl">
      <CardHeader className="flex items-center justify-between gap-2">
        <div>
          <CardTitle>{t('alertRules.title')}</CardTitle>
          <CardDescription>{t('alertRules.description')}</CardDescription>
        </div>
        {metricOptions.length > 0 && editing === null ? (
          <Button size="sm" variant="secondary" onClick={() => setEditing('new')}>
            {t('alertRules.add')}
          </Button>
        ) : null}
      </CardHeader>
      <CardContent>
        {editing !== null ? (
          <AlertRuleForm
            organizationId={organizationId}
            rule={editing === 'new' ? null : editing}
            metricOptions={metricOptions}
            onClose={() => setEditing(null)}
          />
        ) : rulesQuery.isPending ? (
          <RulesSkeleton />
        ) : rulesQuery.isError ? (
          <ErrorState
            title={t('alertRules.loadErrorTitle')}
            description={t('alertRules.loadErrorDescription')}
            retryLabel={t('common.retry')}
            onRetry={() => {
              void rulesQuery.refetch()
            }}
          />
        ) : rules.length === 0 ? (
          <EmptyState
            icon={BellRing}
            title={t('alertRules.emptyTitle')}
            description={t('alertRules.emptyDescription')}
          />
        ) : (
          <ul role="list" aria-label={t('alertRules.title')} className="space-y-3">
            {rules.map((rule) => (
              <AlertRuleRow
                key={rule.id}
                rule={rule}
                organizationId={organizationId}
                canEdit={canEditRule(rule, permissions)}
                onEdit={() => setEditing(rule)}
              />
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}

/** Ossature affichée pendant le premier chargement des règles. */
function RulesSkeleton() {
  return (
    <div className="space-y-3" data-testid="alert-rules-skeleton">
      {Array.from({ length: 2 }, (_, index) => (
        <Skeleton key={index} className="h-16 w-full" />
      ))}
    </div>
  )
}

/** Une ligne de règle : nom, seuil, état et actions. */
function AlertRuleRow({
  rule,
  organizationId,
  canEdit,
  onEdit,
}: {
  rule: AlertRule
  organizationId: string
  canEdit: boolean
  onEdit: () => void
}) {
  const { t, i18n } = useTranslation()
  const deleteRule = useDeleteAlertRule(organizationId)
  const updateRule = useUpdateAlertRule(organizationId)
  const meta = goalMetricMeta(rule.metric_key)
  const name = alertRuleName(rule, t)
  const unit = meta?.unitKey ? ` ${t(meta.unitKey)}` : ''
  const threshold = formatGoalNumber(rule.threshold, i18n.language, meta?.decimals ?? 0)
  const comparisonLabel = t(alertComparisonKey(rule.comparison))
  const periodLabel = t('dashboard.periodDays', { days: rule.period_days })

  function handleDelete() {
    if (window.confirm(t('alertRules.deleteConfirm'))) {
      deleteRule.mutate(rule.id)
    }
  }

  function handleToggle() {
    updateRule.mutate({ ruleId: rule.id, payload: { enabled: !rule.enabled } })
  }

  return (
    <li className="rounded-md border border-border p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-foreground">{name}</p>
          <p className="text-xs text-muted">
            {`${comparisonLabel} ${threshold}${unit} · ${periodLabel}`}
          </p>
        </div>
        <span
          className={cn(
            'inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 text-xs font-medium',
            rule.enabled
              ? 'border-success/30 bg-success/5 text-success'
              : 'border-border bg-surface-muted text-muted',
          )}
        >
          {rule.enabled ? t('alertRules.enabled') : t('alertRules.disabled')}
        </span>
      </div>

      {canEdit ? (
        <div className="mt-2 flex items-center gap-1">
          <Button size="sm" variant="ghost" onClick={onEdit}>
            {t('alertRules.edit')}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={updateRule.isPending}
            onClick={handleToggle}
          >
            {rule.enabled ? t('alertRules.disable') : t('alertRules.enable')}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={deleteRule.isPending}
            onClick={handleDelete}
          >
            {t('alertRules.delete')}
          </Button>
        </div>
      ) : null}

      {deleteRule.isError || updateRule.isError ? (
        <p role="alert" className="mt-2 text-xs text-danger">
          {t('alertRules.updateError')}
        </p>
      ) : null}
    </li>
  )
}
