// Présentation des objectifs (sous-phase 6a-iv) : statut, options d'indicateur et
// droits d'écriture. Aucun libellé en dur : chaque statut renvoie une clé i18n,
// chaque indicateur réutilise le libellé d'un KPI clé (AGENTS.md §7).
import type { GoalStatus, MyPermissionsOut } from '../api/types.ts'
import { KPI_META, type KpiMeta } from '../pulse/format.ts'

/** Aspect d'un statut : clé i18n, teinte du badge et de la barre de progression. */
export interface GoalStatusMeta {
  labelKey: string
  badgeClassName: string
  barClassName: string
}

// Un statut « en dérive » se lit en rouge, « atteint » en vert, « en bonne voie »
// en couleur de marque, « sans données » en neutre — cohérent avec le Pouls.
export const GOAL_STATUS_META: Record<GoalStatus, GoalStatusMeta> = {
  achieved: {
    labelKey: 'goals.statusAchieved',
    badgeClassName: 'border-success/30 bg-success/5 text-success',
    barClassName: 'bg-success',
  },
  on_track: {
    labelKey: 'goals.statusOnTrack',
    badgeClassName: 'border-brand/30 bg-brand-muted text-brand',
    barClassName: 'bg-brand',
  },
  off_track: {
    labelKey: 'goals.statusOffTrack',
    badgeClassName: 'border-danger/30 bg-danger/5 text-danger',
    barClassName: 'bg-danger',
  },
  unknown: {
    labelKey: 'goals.statusUnknown',
    badgeClassName: 'border-border bg-surface-muted text-muted',
    barClassName: 'bg-muted',
  },
}

/** Aspect d'un statut d'objectif (badge + barre). */
export function goalStatusMeta(status: GoalStatus): GoalStatusMeta {
  return GOAL_STATUS_META[status]
}

/** Option sélectionnable dans le formulaire : une cible possible pour un objectif. */
export interface GoalMetricOption {
  value: string
  labelKey: string
  unitKey?: string
  decimals?: number
}

/** Module porteur d'un indicateur : `finance.revenue` → `finance`. */
export function metricModule(metricKey: string): string {
  return metricKey.split('.')[0] ?? ''
}

/**
 * Écriture autorisée sur l'indicateur : un admin a tous les droits, un membre
 * doit avoir le niveau `edit` sur le module de l'indicateur (le backend applique
 * la même règle ; ce test ne fait que masquer les actions inutiles).
 */
export function canEditMetric(
  metricKey: string,
  permissions: MyPermissionsOut | null,
): boolean {
  if (!permissions) {
    return false
  }
  if (permissions.role === 'admin') {
    return true
  }
  return (permissions.modules[metricModule(metricKey)] ?? 'none') === 'edit'
}

/** Métadonnées d'affichage d'un indicateur, si c'est un KPI clé connu. */
export function goalMetricMeta(metricKey: string): KpiMeta | undefined {
  return KPI_META[metricKey]
}

// Le sélecteur d'indicateur propose les KPI clés du Pouls que l'utilisateur peut
// écrire. Le backend accepte n'importe quelle clé canonique ; restreindre le
// formulaire à ces huit KPI garde une liste étiquetée et cohérente avec le
// tableau de bord (décision `DECISIONS.md`).
export function goalMetricOptions(permissions: MyPermissionsOut | null): string[] {
  return Object.keys(KPI_META).filter((metricKey) => canEditMetric(metricKey, permissions))
}

/** Nombre formaté selon la langue, avec la précision d'affichage du KPI. */
export function formatGoalNumber(value: number, language: string, decimals = 0): string {
  return new Intl.NumberFormat(language, { maximumFractionDigits: decimals }).format(value)
}
