// Présentation du Pouls (sous-phase 5f) : métadonnées des KPI clés, tendance et
// horodatage relatif. Aucun libellé en dur : chaque clé canonique renvoie vers
// une clé i18n, traduite par la page (AGENTS.md §7).
import type { AuditLog, PulseKpi } from '../api/types'

/** Libellé, unité et précision d'un KPI : la page traduit les clés i18n. */
export interface KpiMeta {
  labelKey: string
  unitKey?: string
  decimals?: number
}

// Les huit KPI clés exposés par le backend, dans l'ordre des modules. Les
// libellés existants des pages de module sont réutilisés (une seule source).
export const KPI_META: Record<string, KpiMeta> = {
  'finance.revenue': { labelKey: 'finance.kpiRevenue', unitKey: 'common.currencyEur' },
  'finance.margin': { labelKey: 'finance.kpiMargin', unitKey: 'common.currencyEur' },
  'web.visitors': { labelKey: 'web.kpiVisitors', unitKey: 'web.unitVisitors' },
  'web.conversions': { labelKey: 'web.kpiConversions', unitKey: 'web.unitConversions' },
  'social.followers': { labelKey: 'social.kpiFollowers', unitKey: 'social.unitFollowers' },
  'social.engagement_rate': {
    labelKey: 'social.kpiEngagementRate',
    unitKey: 'common.percent',
    decimals: 1,
  },
  'projects.open_tasks': { labelKey: 'projects.kpiOpenTasks', unitKey: 'projects.unitTasks' },
  'projects.avg_progress': {
    labelKey: 'projects.kpiAvgProgress',
    unitKey: 'common.percent',
    decimals: 1,
  },
}

/** Variation en pourcentage entre la valeur courante et la précédente. */
export function kpiTrend(kpi: PulseKpi): number | undefined {
  const previous = kpi.previous_value
  if (previous === null || previous === undefined || previous === 0) {
    return undefined
  }
  return ((kpi.value - previous) / Math.abs(previous)) * 100
}

// Les actions journalisées (services backend) vers une clé i18n sans point :
// i18next lit le point comme un séparateur de chemin, on évite donc la clé brute.
const ACTION_LABEL_KEYS: Record<string, string> = {
  'invitation.created': 'dashboard.actionInvitationCreated',
  'invitation.accepted': 'dashboard.actionInvitationAccepted',
  'invitation.revoked': 'dashboard.actionInvitationRevoked',
  'membership.permissions.updated': 'dashboard.actionPermissionsUpdated',
  'membership.revoked': 'dashboard.actionMemberRevoked',
  'legal.profile.updated': 'dashboard.actionLegalUpdated',
  'legal.profile.refreshed': 'dashboard.actionLegalRefreshed',
  'legal.profile.diverged': 'dashboard.actionLegalDiverged',
}

/** Clé i18n du libellé d'une entrée du journal (repli générique si inconnue). */
export function actionLabelKey(entry: AuditLog): string {
  return ACTION_LABEL_KEYS[entry.action] ?? 'dashboard.actionUnknown'
}

/** Horodatage relatif localisé (« il y a 3 minutes », « hier »). */
export function formatRelativeTime(iso: string, language: string, now = new Date()): string {
  const diffMinutes = Math.round((new Date(iso).getTime() - now.getTime()) / 60_000)
  const formatter = new Intl.RelativeTimeFormat(language, { numeric: 'auto' })
  if (Math.abs(diffMinutes) < 60) {
    return formatter.format(diffMinutes, 'minute')
  }
  const diffHours = Math.round(diffMinutes / 60)
  if (Math.abs(diffHours) < 24) {
    return formatter.format(diffHours, 'hour')
  }
  return formatter.format(Math.round(diffHours / 24), 'day')
}
