// Requêtes du Pouls (sous-phase 5f). Les queryFn sont séparées des composants
// (règle react-refresh) : les hooks n'importent jamais un composant. Le Pouls
// agrège, côté backend, les modules autorisés du membre ; le frontend ne filtre
// donc rien lui-même (AGENTS.md §8).
import { useQuery } from '@tanstack/react-query'
import { api, ApiError } from '../api/client'
import type { Pulse } from '../api/types'
import { POLLING_INTERVAL_MS } from '../metrics/queries.ts'

export const pulseKeys = {
  pulse: (organizationId: string) => ['pulse', organizationId] as const,
}

export async function fetchPulse(organizationId: string): Promise<Pulse> {
  const result = await api.GET('/api/v1/organizations/{organization_id}/pulse', {
    params: { path: { organization_id: organizationId } },
  })
  if (!result.response.ok) {
    throw ApiError.from(result.response.status, result.error)
  }
  return result.data!
}

export function usePulse(organizationId: string) {
  return useQuery({
    queryKey: pulseKeys.pulse(organizationId),
    queryFn: () => fetchPulse(organizationId),
    // Polling toutes les 5 min : le pouls se rafraîchit sans geste (SPEC §6).
    refetchInterval: POLLING_INTERVAL_MS,
    retry: false,
    refetchOnWindowFocus: false,
  })
}
