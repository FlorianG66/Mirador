// Requêtes métriques TanStack Query (sous-phase 5a). Les queryFn sont séparées
// des composants (règle react-refresh) : un hook n'importe jamais un composant.
import { api, ApiError } from '../api/client'
import type { MetricSeries } from '../api/types'

export const metricsKeys = {
  metric: (organizationId: string, metricKey: string) =>
    ['metrics', organizationId, metricKey] as const,
  panel: (organizationId: string, panel: 'finance') =>
    ['metrics', organizationId, 'panel', panel] as const,
}

/** Intervalles constants de la SPA : le polling des widgets de module (SPEC §6). */
export const POLLING_INTERVAL_MS = 5 * 60 * 1000

/** Nombre de points demandés par défaut pour les widgets (fenêtre glissante). */
export const DEFAULT_LIMIT = 60

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
