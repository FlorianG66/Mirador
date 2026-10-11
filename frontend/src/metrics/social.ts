// Panneau réseaux sociaux (sous-phase 5c, SPEC §3) : les 9 séries canoniques
// chargées ensemble, avec polling 5 minutes. Une série absente du registre (404)
// compte comme « pas encore connectée » ; toute autre erreur remonte à la page.
// Même patron que `finance.ts` / `web.ts`.
import { useQuery } from '@tanstack/react-query'
import type { MetricSeries, SocialMetricKey } from '../api/types'
import {
  DEFAULT_LIMIT,
  POLLING_INTERVAL_MS,
  fetchMetricSeries,
  isNotFound,
  metricsKeys,
} from './queries.ts'

export const SOCIAL_METRIC_KEYS: SocialMetricKey[] = [
  'social.followers',
  'social.followers_growth',
  'social.impressions',
  'social.reach',
  'social.engagements',
  'social.engagement_rate',
  'social.mentions',
  'social.posts',
  'social.top_posts',
]

export interface SocialPanel {
  /** Les séries présentes (limitées aux points chargés par le serveur). */
  series: Partial<Record<SocialMetricKey, MetricSeries>>
  /** Les séries sans donnée (404 pour l'organisation active). */
  missing: SocialMetricKey[]
}

export async function fetchSocialPanel(
  organizationId: string,
  limit = DEFAULT_LIMIT,
): Promise<SocialPanel> {
  const results = await Promise.all(
    SOCIAL_METRIC_KEYS.map(async (key) => {
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

  const series: SocialPanel['series'] = {}
  const missing: SocialMetricKey[] = []
  for (const [key, value] of results) {
    if (value === null) {
      missing.push(key)
    } else {
      series[key] = value
    }
  }
  return { series, missing }
}

export function useSocialPanel(organizationId: string, limit = DEFAULT_LIMIT) {
  return useQuery({
    queryKey: metricsKeys.panel(organizationId, 'social'),
    queryFn: () => fetchSocialPanel(organizationId, limit),
    // Polling toutes les 5 min : les données se rafraîchissent sans geste.
    refetchInterval: POLLING_INTERVAL_MS,
    retry: false,
    refetchOnWindowFocus: false,
  })
}
