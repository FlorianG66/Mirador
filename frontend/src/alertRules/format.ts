// Présentation des règles d'alerte (sous-phase 6c-iii) : libellé d'une règle,
// sens du seuil et options d'indicateur. Aucun texte en dur : le sens renvoie une
// clé i18n, l'indicateur réutilise le libellé d'un KPI clé (AGENTS.md §7).
import type { AlertComparison, AlertRule, MyPermissionsOut } from '../api/types.ts'
import { canEditMetric, goalMetricMeta, goalMetricOptions } from '../goals/format.ts'

/** Clé i18n du sens de franchissement d'un seuil. */
const COMPARISON_KEYS: Record<AlertComparison, string> = {
  above: 'alertRules.comparisonAbove',
  below: 'alertRules.comparisonBelow',
}

/** Clé i18n décrivant le sens d'une règle (« au-dessus de », « en dessous de »). */
export function alertComparisonKey(comparison: AlertComparison): string {
  return COMPARISON_KEYS[comparison]
}

/** Libellé d'une règle : libellé saisi, sinon libellé i18n de l'indicateur. */
export function alertRuleName(rule: AlertRule, t: (key: string) => string): string {
  if (rule.label) {
    return rule.label
  }
  const meta = goalMetricMeta(rule.metric_key)
  return meta ? t(meta.labelKey) : rule.metric_key
}

/**
 * Écriture autorisée sur la règle : suit la même règle que les objectifs — `edit`
 * sur le module de la métrique (l'admin a tout). Le backend applique la règle ;
 * ce test ne fait que masquer les actions vouées à un 403.
 */
export function canEditRule(rule: AlertRule, permissions: MyPermissionsOut | null): boolean {
  return canEditMetric(rule.metric_key, permissions)
}

/** Indicateurs proposés à la création : les KPI clés que l'utilisateur peut écrire. */
export function alertMetricOptions(permissions: MyPermissionsOut | null): string[] {
  return goalMetricOptions(permissions)
}

export { canEditMetric, goalMetricMeta }
