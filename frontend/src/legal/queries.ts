// Requêtes de la fiche légale (sous-phase 5e-c). Les queryFn sont séparées des
// composants (règle react-refresh) : un hook n'importe jamais un composant.
// Contrairement aux panneaux de métriques, la fiche est un objet unique (pas de
// polling) : lecture, saisie manuelle (PUT) et rafraîchissement registre (POST).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, ApiError, unwrap } from '../api/client'
import type { LegalProfile, LegalProfileUpdate } from '../api/types'

const LEGAL_PATH = '/api/v1/organizations/{organization_id}/legal'
const LEGAL_REFRESH_PATH = '/api/v1/organizations/{organization_id}/legal/refresh'

export const legalKeys = {
  profile: (organizationId: string) => ['legal', organizationId, 'profile'] as const,
}

export async function fetchLegalProfile(organizationId: string): Promise<LegalProfile> {
  const result = await api.GET(LEGAL_PATH, {
    params: { path: { organization_id: organizationId } },
  })
  if (!result.response.ok) {
    throw ApiError.from(result.response.status, result.error)
  }
  return result.data!
}

export function useLegalProfile(organizationId: string) {
  return useQuery({
    queryKey: legalKeys.profile(organizationId),
    queryFn: () => fetchLegalProfile(organizationId),
    retry: false,
    refetchOnWindowFocus: false,
  })
}

export function useUpdateLegalProfile(organizationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: LegalProfileUpdate) =>
      unwrap(
        api.PUT(LEGAL_PATH, {
          params: { path: { organization_id: organizationId } },
          body: payload,
        }),
      ),
    onSuccess: (data) => {
      queryClient.setQueryData(legalKeys.profile(organizationId), data)
    },
  })
}

export function useRefreshLegalProfile(organizationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () =>
      unwrap(api.POST(LEGAL_REFRESH_PATH, {
        params: { path: { organization_id: organizationId } },
      })),
    onSuccess: (data) => {
      queryClient.setQueryData(legalKeys.profile(organizationId), data)
    },
  })
}
