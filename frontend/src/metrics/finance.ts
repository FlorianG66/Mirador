// Panneau financier (sous-phase 5a, SPEC §3) : les 8 séries canoniques chargées
// ensemble, avec polling 5 minutes. Une série absente du registre (404) compte
// comme « pas encore connectée » ; toute autre erreur remonte à la page.
import { useQuery } from '@tanstack/react-query'
import type { ApiError } from '../api/client'
import type { FinanceMetricKey, MetricSeries } from '../api/types'
import {
  DEFAULT_LIMIT,
  POLLING_INTERVAL_MS,
  fetchMetricSeries,
  metricsKeys,
} from './queries.ts'

export const FINANCE_METRIC_KEYS: FinanceMetricKey[] = [
  'finance.revenue',
  'finance.expenses',
  'finance.margin',
  'finance.cash',
  'finance.budget',
  'finance.invoices_outstanding',
  'finance.top_clients',
  'finance.top_suppliers',
]

export interface FinancePanel {
  /** Les séries présentes (limitées aux points chargés par le serveur). */
  series: Partial<Record<FinanceMetricKey, MetricSeries>>
  /** Les séries sans donnée (404 pour l'organisation active). */
  missing: FinanceMetricKey[]
}

/** Distingue une série inexistante (404) d'une vraie panne. */
export function isNotFound(error: unknown): error is ApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'status' in error &&
    (error as ApiError).status === 404
  )
}

export async function fetchFinancePanel(
  organizationId: string,
  limit = DEFAULT_LIMIT,
): Promise<FinancePanel> {
  const results = await Promise.all(
    FINANCE_METRIC_KEYS.map(async (key) => {
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

  const series: FinancePanel['series'] = {}
  const missing: FinanceMetricKey[] = []
  for (const [key, value] of results) {
    if (value === null) {
      missing.push(key)
    } else {
      series[key] = value
    }
  }
  return { series, missing }
}

export function useFinancePanel(organizationId: string, limit = DEFAULT_LIMIT) {
  return useQuery({
    queryKey: metricsKeys.panel(organizationId, 'finance'),
    queryFn: () => fetchFinancePanel(organizationId, limit),
    // Polling toutes les 5 min : les données se rafraîchissent sans geste.
    refetchInterval: POLLING_INTERVAL_MS,
    retry: false,
    refetchOnWindowFocus: false,
  })
}
