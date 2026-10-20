// Formulaire de règle d'alerte (sous-phase 6c-iii) : création et édition. Le
// sélecteur d'indicateur est limité aux KPI clés que l'utilisateur peut écrire ;
// la fenêtre réutilise le sélecteur de période. Le libellé est optionnel — sans
// lui, l'affichage retombe sur le nom du KPI.
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import type { AlertComparison, AlertRule, AlertRuleCreate } from '../api/types.ts'
import { Button } from '../components/ui/Button.tsx'
import { PeriodSelect } from '../components/ui/PeriodSelect.tsx'
import { DEFAULT_PERIOD_DAYS, PERIOD_OPTIONS } from '../metrics/queries.ts'
import { goalMetricMeta } from '../goals/format.ts'
import { useCreateAlertRule, useUpdateAlertRule } from './queries.ts'

const INPUT_CLASS =
  'h-10 w-full rounded-md border border-border bg-background px-3 text-foreground outline-none focus-visible:ring-2 focus-visible:ring-brand'

export interface AlertRuleFormProps {
  organizationId: string
  /** Règle à modifier, ou `null` pour une création. */
  rule: AlertRule | null
  /** Clés des indicateurs que l'utilisateur peut écrire. */
  metricOptions: string[]
  onClose: () => void
}

export function AlertRuleForm({ organizationId, rule, metricOptions, onClose }: AlertRuleFormProps) {
  const { t } = useTranslation()
  const createRule = useCreateAlertRule(organizationId)
  const updateRule = useUpdateAlertRule(organizationId)
  const [metricKey, setMetricKey] = useState(rule?.metric_key ?? metricOptions[0] ?? '')
  const [comparison, setComparison] = useState<AlertComparison>(rule?.comparison ?? 'above')
  const [threshold, setThreshold] = useState(rule ? String(rule.threshold) : '')
  const [periodDays, setPeriodDays] = useState<number>(rule?.period_days ?? DEFAULT_PERIOD_DAYS)
  const [label, setLabel] = useState(rule?.label ?? '')

  // Une règle existante peut viser un KPI absent de la liste d'options : on
  // l'ajoute pour ne pas le réécrire à l'aveugle.
  const options = metricOptions.includes(metricKey)
    ? metricOptions
    : [metricKey, ...metricOptions].filter((key) => key !== '')

  const parsedThreshold = Number(threshold)
  const canSubmit =
    metricKey !== '' && threshold.trim() !== '' && Number.isFinite(parsedThreshold)
  const isSaving = createRule.isPending || updateRule.isPending
  const hasError = createRule.isError || updateRule.isError

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!canSubmit) {
      return
    }
    const payload: AlertRuleCreate = {
      metric_key: metricKey,
      label: label.trim() === '' ? null : label.trim(),
      comparison,
      threshold: parsedThreshold,
      period_days: periodDays,
      enabled: rule?.enabled ?? true,
    }
    try {
      if (rule) {
        await updateRule.mutateAsync({ ruleId: rule.id, payload })
      } else {
        await createRule.mutateAsync(payload)
      }
      onClose()
    } catch {
      // L'échec est affiché via `hasError` : on garde le formulaire ouvert.
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <label className="block space-y-1 text-sm">
        <span className="font-medium">{t('alertRules.metricLabel')}</span>
        <select
          value={metricKey}
          onChange={(event) => setMetricKey(event.target.value)}
          className={INPUT_CLASS}
        >
          {options.map((key) => {
            const meta = goalMetricMeta(key)
            return (
              <option key={key} value={key}>
                {meta ? t(meta.labelKey) : key}
              </option>
            )
          })}
        </select>
      </label>

      <label className="block space-y-1 text-sm">
        <span className="font-medium">{t('alertRules.comparisonLabel')}</span>
        <select
          value={comparison}
          onChange={(event) => setComparison(event.target.value as AlertComparison)}
          className={INPUT_CLASS}
        >
          <option value="above">{t('alertRules.comparisonAbove')}</option>
          <option value="below">{t('alertRules.comparisonBelow')}</option>
        </select>
      </label>

      <label className="block space-y-1 text-sm">
        <span className="font-medium">{t('alertRules.thresholdLabel')}</span>
        <input
          type="number"
          inputMode="decimal"
          step="any"
          value={threshold}
          onChange={(event) => setThreshold(event.target.value)}
          className={INPUT_CLASS}
        />
      </label>

      <div className="space-y-1 text-sm">
        <span className="font-medium">{t('alertRules.windowLabel')}</span>
        <PeriodSelect
          label={t('alertRules.windowLabel')}
          value={periodDays}
          onChange={setPeriodDays}
          options={PERIOD_OPTIONS.map((days) => ({
            value: days,
            label: t('dashboard.periodDays', { days }),
          }))}
        />
      </div>

      <label className="block space-y-1 text-sm">
        <span className="font-medium">{t('alertRules.labelLabel')}</span>
        <input
          type="text"
          value={label}
          maxLength={120}
          placeholder={t('alertRules.labelPlaceholder')}
          onChange={(event) => setLabel(event.target.value)}
          className={INPUT_CLASS}
        />
      </label>

      {hasError ? (
        <p role="alert" className="text-sm text-danger">
          {t('alertRules.saveError')}
        </p>
      ) : null}

      <div className="flex items-center gap-2">
        <Button type="submit" disabled={!canSubmit || isSaving}>
          {isSaving ? t('alertRules.saving') : t('alertRules.save')}
        </Button>
        <Button type="button" variant="secondary" onClick={onClose} disabled={isSaving}>
          {t('alertRules.cancel')}
        </Button>
      </div>
    </form>
  )
}
