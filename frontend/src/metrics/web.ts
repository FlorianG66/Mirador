// Panneau web analytics (sous-phase 5b, SPEC §3) : les 10 séries canoniques
// chargées ensemble, avec polling 5 minutes. Une série absente du registre (404)
// compte comme « pas encore connectée » ; toute autre erreur remonte à la page.
// Même patron que `finance.ts`.
import { useQuery } from '@tanstack/react-query'
import type { MetricSeries, WebMetricKey } from '../api/types'
import {
  DEFAULT_LIMIT,
  POLLING_INTERVAL_MS,
  fetchMetricSeries,
  isNotFound,
  metricsKeys,
} from './queries.ts'

export const WEB_METRIC_KEYS: WebMetricKey[] = [
  'web.sessions',
  'web.visitors',
  'web.pageviews',
  'web.engagement_rate',
  'web.avg_session_duration',
  'web.conversions',
  'web.traffic_sources',
  'web.top_pages',
  'web.devices',
  'web.countries',
]

export interface WebPanel {
  /** Les séries présentes (limitées aux points chargés par le serveur). */
  series: Partial<Record<WebMetricKey, MetricSeries>>
  /** Les séries sans donnée (404 pour l'organisation active). */
  missing: WebMetricKey[]
}

export async function fetchWebPanel(
  organizationId: string,
  limit = DEFAULT_LIMIT,
): Promise<WebPanel> {
  const results = await Promise.all(
    WEB_METRIC_KEYS.map(async (key) => {
      try {
        const series = await fetchMetricSeries(organizationId, key, limit)
        return [key, series] as const
      } catch (error) {
        if (isNotFound(error)) {
          return [key, null] as const
        }
        throw error
      }
    }),
  )

  const series: WebPanel['series'] = {}
  const missing: WebMetricKey[] = []
  for (const [key, value] of results) {
    if (value === null) {
      missing.push(key)
    } else {
      series[key] = value
    }
  }
  return { series, missing }
}

export function useWebPanel(organizationId: string, limit = DEFAULT_LIMIT) {
  return useQuery({
    queryKey: metricsKeys.panel(organizationId, 'web'),
    queryFn: () => fetchWebPanel(organizationId, limit),
    // Polling toutes les 5 min : les données se rafraîchissent sans geste.
    refetchInterval: POLLING_INTERVAL_MS,
    retry: false,
    refetchOnWindowFocus: false,
  })
}
