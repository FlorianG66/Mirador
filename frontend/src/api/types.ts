// Alias de types métier dérivés du schéma OpenAPI généré (source unique de
// vérité). Évite d'importer `components['schemas'][...]` partout dans l'app.
import type { components } from './schema'

export type MeResponse = components['schemas']['MeResponse']
export type MembershipOut = components['schemas']['MembershipOut']
export type MyPermissionsOut = components['schemas']['MyPermissionsOut']
export type ModuleKey = components['schemas']['Module']
export type PermissionLevel = components['schemas']['PermissionLevel']
export type Role = components['schemas']['Role']
export type MetricPoint = components['schemas']['MetricPoint']
export type MetricSeries = components['schemas']['MetricSeries']

/**
 * Les clés canoniques du panneau financier (sous-phase 5a). Sert à décrire le
 * contrat des données consommées par la page Finance — chaque clé est un suffixe
 * `module.metric` du schéma, pas une invention du frontend.
 */
export type FinanceMetricKey =
  | 'finance.revenue'
  | 'finance.expenses'
  | 'finance.margin'
  | 'finance.cash'
  | 'finance.budget'
  | 'finance.invoices_outstanding'
  | 'finance.top_clients'
  | 'finance.top_suppliers'

/**
 * Les clés canoniques du panneau web analytics (sous-phase 5b). Même contrat que
 * la finance : chaque clé est un suffixe `module.metric` du schéma, pas une
 * invention du frontend.
 */
export type WebMetricKey =
  | 'web.sessions'
  | 'web.visitors'
  | 'web.pageviews'
  | 'web.engagement_rate'
  | 'web.avg_session_duration'
  | 'web.conversions'
  | 'web.traffic_sources'
  | 'web.top_pages'
  | 'web.devices'
  | 'web.countries'
