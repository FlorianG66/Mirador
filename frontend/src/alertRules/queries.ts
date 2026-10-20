// Requêtes des règles d'alerte (sous-phase 6c-iii). Les queryFn et mutations
// vivent hors des composants (règle react-refresh). Toute écriture invalide la
// liste : le backend recalculera l'évaluation au prochain passage du worker.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, api, unwrap } from '../api/client.ts'
import type { AlertRule, AlertRuleCreate, AlertRuleUpdate } from '../api/types.ts'

const RULES_PATH = '/api/v1/organizations/{organization_id}/alert-rules' as const
const RULE_PATH = '/api/v1/organizations/{organization_id}/alert-rules/{rule_id}' as const

export const alertRulesKeys = {
  list: (organizationId: string) => ['alert-rules', organizationId] as const,
}

export function fetchAlertRules(organizationId: string): Promise<AlertRule[]> {
  return unwrap(
    api.GET(RULES_PATH, { params: { path: { organization_id: organizationId } } }),
  )
}

export function useAlertRules(organizationId: string) {
  return useQuery({
    queryKey: alertRulesKeys.list(organizationId),
    queryFn: () => fetchAlertRules(organizationId),
    enabled: Boolean(organizationId),
    retry: false,
    refetchOnWindowFocus: false,
  })
}

export function useCreateAlertRule(organizationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: AlertRuleCreate) =>
      unwrap(
        api.POST(RULES_PATH, {
          params: { path: { organization_id: organizationId } },
          body: payload,
        }),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: alertRulesKeys.list(organizationId) }),
  })
}

export function useUpdateAlertRule(organizationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ ruleId, payload }: { ruleId: string; payload: AlertRuleUpdate }) =>
      unwrap(
        api.PATCH(RULE_PATH, {
          params: { path: { organization_id: organizationId, rule_id: ruleId } },
          body: payload,
        }),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: alertRulesKeys.list(organizationId) }),
  })
}

export function useDeleteAlertRule(organizationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (ruleId: string) => {
      // 204 sans corps : `unwrap` ne convient pas, on contrôle le statut seul.
      const result = await api.DELETE(RULE_PATH, {
        params: { path: { organization_id: organizationId, rule_id: ruleId } },
      })
      if (!result.response.ok) {
        throw ApiError.from(result.response.status, result.error)
      }
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: alertRulesKeys.list(organizationId) }),
  })
}
