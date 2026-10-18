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
export type MetricAggregation = components['schemas']['MetricAggregation']
export type MetricComparison = components['schemas']['MetricComparison']
export type MetricComparisonSummary = components['schemas']['MetricComparisonSummary']
export type LegalProfile = components['schemas']['LegalProfileOut']
export type LegalProfileUpdate = components['schemas']['LegalProfileUpdate']
export type LegalDirector = components['schemas']['LegalDirectorOut']
export type LegalIdentifier = components['schemas']['LegalIdentifierOut']
export type LegalFieldSource = components['schemas']['FieldSourceOut']
export type Pulse = components['schemas']['PulseOut']
export type PulseKpi = components['schemas']['PulseKpiOut']
export type PulseHealth = components['schemas']['PulseHealthOut']
export type AuditLog = components['schemas']['AuditLogOut']
export type Dashboard = components['schemas']['DashboardOut']
export type DashboardWidget = components['schemas']['DashboardWidgetOut']
export type DashboardPlacement = components['schemas']['DashboardPlacement']
export type DashboardLayoutUpdate = components['schemas']['DashboardLayoutUpdate']
export type WidgetKind = components['schemas']['WidgetKind']

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

/**
 * Les clés canoniques du panneau réseaux sociaux (sous-phase 5c). Même contrat
 * que la finance et le web : chaque clé est un suffixe `module.metric` du schéma.
 */
export type SocialMetricKey =
  | 'social.followers'
  | 'social.followers_growth'
  | 'social.impressions'
  | 'social.reach'
  | 'social.engagements'
  | 'social.engagement_rate'
  | 'social.mentions'
  | 'social.posts'
  | 'social.top_posts'

/**
 * Les clés canoniques du panneau projets & tâches (sous-phase 5d). Même contrat
 * que les autres modules : chaque clé est un suffixe `module.metric` du schéma,
 * jamais une invention du frontend.
 */
export type Goal = components['schemas']['GoalOut']
export type GoalCreate = components['schemas']['GoalCreate']
export type GoalUpdate = components['schemas']['GoalUpdate']
export type GoalDirection = components['schemas']['GoalDirection']
export type GoalStatus = components['schemas']['GoalStatus']
export type GoalProgress = components['schemas']['GoalProgress']

export type ProjectMetricKey =
  | 'projects.tasks_done'
  | 'projects.tasks_created'
  | 'projects.open_tasks'
  | 'projects.overdue_tasks'
  | 'projects.avg_completion_time'
  | 'projects.avg_progress'
  | 'projects.active_projects'
  | 'projects.tasks_by_status'
  | 'projects.person_load'
  | 'projects.upcoming_milestones'

export type Notification = components['schemas']['NotificationOut']
export type NotificationList = components['schemas']['NotificationListOut']
