// Requêtes métriques TanStack Query (sous-phase 5a). Les queryFn sont séparées
// des composants (règle react-refresh) : un hook n'importe jamais un composant.
import { api, ApiError } from '../api/client'
import type { MetricComparison, MetricSeries } from '../api/types'

export const metricsKeys = {
  metric: (organizationId: string, metricKey: string) =>
    ['metrics', organizationId, metricKey] as const,
  panel: (organizationId: string, panel: 'finance' | 'web' | 'social' | 'projects') =>
    ['metrics', organizationId, 'panel', panel] as const,
  comparison: (organizationId: string, metricKey: string, days: number) =>
    ['metrics', organizationId, metricKey, 'comparison', days] as const,
}

/** Intervalles constants de la SPA : le polling des widgets de module (SPEC §6). */
export const POLLING_INTERVAL_MS = 5 * 60 * 1000

/** Nombre de points demandés par défaut pour les widgets (fenêtre glissante). */
export const DEFAULT_LIMIT = 60

/**
 * Fenêtres proposées par le sélecteur de période du tableau de bord (SPEC §4,
 * phase 6a) : la fenêtre courante est comparée à la précédente, de même longueur.
 */
export const PERIOD_OPTIONS = [7, 30, 90] as const
export type PeriodDays = (typeof PERIOD_OPTIONS)[number]
export const DEFAULT_PERIOD_DAYS: PeriodDays = 30

/**
 * Distingue une série inexistante (404, module non connecté) d'une vraie panne.
 * Le panneau s'en sert pour marquer une clé « absente » sans échouer l'ensemble.
 */
export function isNotFound(error: unknown): error is ApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'status' in error &&
    (error as ApiError).status === 404
  )
}

export async function fetchMetricSeries(
  organizationId: string,
  metricKey: string,
  limit = DEFAULT_LIMIT,
): Promise<MetricSeries> {
  const result = await api.GET(
    '/api/v1/organizations/{organization_id}/metrics/{metric_key}',
    {
      params: {
        path: { organization_id: organizationId, metric_key: metricKey },
        query: { limit },
      },
    },
  )
  if (!result.response.ok) {
    throw ApiError.from(result.response.status, result.error)
  }
  return result.data!
}

/**
 * Agrégat d'une métrique sur `days` jours, comparé à la période précédente
 * équivalente (phase 6a). Un 404 (aucune donnée sur la fenêtre) doit être lu
 * comme « pas de donnée », pas comme une panne : l'appelant retombe alors sur la
 * dernière valeur connue du Pouls plutôt que d'échouer.
 */
export async function fetchMetricComparison(
  organizationId: string,
  metricKey: string,
  days: number,
): Promise<MetricComparison> {
  const result = await api.GET(
    '/api/v1/organizations/{organization_id}/metrics/{metric_key}/comparison',
    {
      params: {
        path: { organization_id: organizationId, metric_key: metricKey },
        query: { days },
      },
    },
  )
  if (!result.response.ok) {
    throw ApiError.from(result.response.status, result.error)
  }
  return result.data!
}
