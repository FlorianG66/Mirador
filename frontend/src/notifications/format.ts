// Présentation des notifications in-app (sous-phase 6c-ii). Aucun libellé en
// dur : chaque type (`kind`) renvoie vers des clés i18n et chaque valeur est
// formatée pour la langue courante (AGENTS.md §7). Les `kind` backend portent un
// point (« goal.achieved ») que i18next lirait comme un séparateur de chemin : on
// passe donc par une table de correspondance explicite, jamais par la clé brute.
import type { Notification } from '../api/types.ts'
import { formatGoalNumber, goalMetricMeta } from '../goals/format.ts'

/** Texte final d'une notification, déjà traduit et formaté. */
export interface NotificationText {
  title: string
  body: string
}

type Translate = (key: string, options?: Record<string, unknown>) => string

const TITLE_BODY_KEYS: Record<string, { title: string; body: string }> = {
  'goal.achieved': {
    title: 'notifications.goalAchievedTitle',
    body: 'notifications.goalAchievedBody',
  },
  'goal.off_track': {
    title: 'notifications.goalOffTrackTitle',
    body: 'notifications.goalOffTrackBody',
  },
  'legal.diverged': {
    title: 'notifications.legalDivergedTitle',
    body: 'notifications.legalDivergedBody',
  },
}

const FALLBACK_KEYS = {
  title: 'notifications.unknownTitle',
  body: 'notifications.unknownBody',
}

/** Lit une chaîne dans les `params` JSON de la notification (sinon chaîne vide). */
function paramString(params: Record<string, unknown>, key: string): string {
  const value = params[key]
  return typeof value === 'string' ? value : ''
}

/** Libellé de l'indicateur visé (KPI clé connu, sinon la clé canonique brute). */
function metricLabel(metricKey: string, t: Translate): string {
  const meta = goalMetricMeta(metricKey)
  return meta ? t(meta.labelKey) : metricKey
}

/** Cible formatée selon la précision d'affichage du KPI (sinon entier). */
function targetLabel(value: unknown, metricKey: string, language: string): string {
  if (typeof value !== 'number') return ''
  return formatGoalNumber(value, language, goalMetricMeta(metricKey)?.decimals ?? 0)
}

/**
 * Traduit une notification en titre + corps. Les `params` ne sont lus que pour
 * les types connus ; toute autre valeur retombe sur un texte générique, sans
 * jamais exposer de contenu non traduit.
 */
export function describeNotification(
  notification: Notification,
  t: Translate,
  language: string,
): NotificationText {
  const keys = TITLE_BODY_KEYS[notification.kind] ?? FALLBACK_KEYS
  const params = notification.params

  if (notification.kind === 'goal.achieved' || notification.kind === 'goal.off_track') {
    const metricKey = paramString(params, 'metric_key')
    return {
      title: t(keys.title),
      body: t(keys.body, {
        metric: metricLabel(metricKey, t),
        target: targetLabel(params.target_value, metricKey, language),
      }),
    }
  }

  return { title: t(keys.title), body: t(keys.body) }
}
