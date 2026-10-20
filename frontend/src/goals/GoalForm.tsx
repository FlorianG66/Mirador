// Formulaire d'objectif (sous-phase 6a-iv) : création et édition dans le panneau
// du tableau de bord. Le sélecteur d'indicateur est limité aux KPI clés que
// l'utilisateur peut écrire ; la fenêtre réutilise le sélecteur de période. Le
// libellé est optionnel — sans lui, l'affichage retombe sur le nom du KPI.
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import type { Goal, GoalCreate, GoalDirection } from '../api/types.ts'
import { Button } from '../components/ui/Button.tsx'
import { PeriodSelect } from '../components/ui/PeriodSelect.tsx'
import { DEFAULT_PERIOD_DAYS, PERIOD_OPTIONS } from '../metrics/queries.ts'
import { goalMetricMeta } from './format.ts'
import { useCreateGoal, useUpdateGoal } from './queries.ts'

const INPUT_CLASS =
  'h-10 w-full rounded-md border border-border bg-background px-3 text-foreground outline-none focus-visible:ring-2 focus-visible:ring-brand'

export interface GoalFormProps {
  organizationId: string
  /** Objectif à modifier, ou `null` pour une création. */
  goal: Goal | null
  /** Clés des indicateurs que l'utilisateur peut écrire. */
  metricOptions: string[]
  onClose: () => void
}

export function GoalForm({ organizationId, goal, metricOptions, onClose }: GoalFormProps) {
  const { t } = useTranslation()
  const createGoal = useCreateGoal(organizationId)
  const updateGoal = useUpdateGoal(organizationId)
  const [metricKey, setMetricKey] = useState(goal?.metric_key ?? metricOptions[0] ?? '')
  const [direction, setDirection] = useState<GoalDirection>(goal?.direction ?? 'at_least')
  const [targetValue, setTargetValue] = useState(goal ? String(goal.target_value) : '')
  const [periodDays, setPeriodDays] = useState<number>(goal?.period_days ?? DEFAULT_PERIOD_DAYS)
  const [label, setLabel] = useState(goal?.label ?? '')

  // Un objectif existant peut viser un KPI absent de la liste d'options (créé par
  // un autre écran) : on l'ajoute pour ne pas le réécrire à l'aveugle.
  const options = metricOptions.includes(metricKey)
    ? metricOptions
    : [metricKey, ...metricOptions].filter((key) => key !== '')

  const parsedTarget = Number(targetValue)
  const canSubmit =
    metricKey !== '' && targetValue.trim() !== '' && Number.isFinite(parsedTarget)
  const isSaving = createGoal.isPending || updateGoal.isPending
  const hasError = createGoal.isError || updateGoal.isError

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!canSubmit) {
      return
    }
    const payload: GoalCreate = {
      metric_key: metricKey,
      label: label.trim() === '' ? null : label.trim(),
      direction,
      target_value: parsedTarget,
      period_days: periodDays,
    }
    try {
      if (goal) {
        await updateGoal.mutateAsync({ goalId: goal.id, payload })
      } else {
        await createGoal.mutateAsync(payload)
      }
      onClose()
    } catch {
      // L'échec est affiché via `hasError` : on garde le formulaire ouvert.
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <label className="block space-y-1 text-sm">
        <span className="font-medium">{t('goals.metricLabel')}</span>
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
        <span className="font-medium">{t('goals.directionLabel')}</span>
        <select
          value={direction}
          onChange={(event) => setDirection(event.target.value as GoalDirection)}
          className={INPUT_CLASS}
        >
          <option value="at_least">{t('goals.directionAtLeast')}</option>
          <option value="at_most">{t('goals.directionAtMost')}</option>
        </select>
      </label>

      <label className="block space-y-1 text-sm">
        <span className="font-medium">{t('goals.targetLabel')}</span>
        <input
          type="number"
          inputMode="decimal"
          step="any"
          value={targetValue}
          onChange={(event) => setTargetValue(event.target.value)}
          className={INPUT_CLASS}
        />
      </label>

      <div className="space-y-1 text-sm">
        <span className="font-medium">{t('goals.windowLabel')}</span>
        <PeriodSelect
          label={t('goals.windowLabel')}
          value={periodDays}
          onChange={setPeriodDays}
          options={PERIOD_OPTIONS.map((days) => ({
            value: days,
            label: t('dashboard.periodDays', { days }),
          }))}
        />
      </div>

      <label className="block space-y-1 text-sm">
        <span className="font-medium">{t('goals.labelLabel')}</span>
        <input
          type="text"
          value={label}
          maxLength={120}
          placeholder={t('goals.labelPlaceholder')}
          onChange={(event) => setLabel(event.target.value)}
          className={INPUT_CLASS}
        />
      </label>

      {hasError ? (
        <p role="alert" className="text-sm text-danger">
          {t('goals.saveError')}
        </p>
      ) : null}

      <div className="flex items-center gap-2">
        <Button type="submit" disabled={!canSubmit || isSaving}>
          {isSaving ? t('goals.saving') : t('goals.save')}
        </Button>
        <Button type="button" variant="secondary" onClick={onClose} disabled={isSaving}>
          {t('goals.cancel')}
        </Button>
      </div>
    </form>
  )
}
