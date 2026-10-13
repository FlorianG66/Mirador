// Requêtes des objectifs (sous-phase 6a-iv). Les queryFn/mutations sont séparées
// des composants (règle react-refresh). La progression et la dérive sont
// recalculées par le backend à chaque lecture : toute écriture invalide donc la
// liste, jamais un état local.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, api, unwrap } from '../api/client.ts'
import type { Goal, GoalCreate, GoalUpdate } from '../api/types.ts'

const GOALS_PATH = '/api/v1/organizations/{organization_id}/goals' as const
const GOAL_PATH = '/api/v1/organizations/{organization_id}/goals/{goal_id}' as const

export const goalsKeys = {
  list: (organizationId: string) => ['goals', organizationId] as const,
}

export function fetchGoals(organizationId: string): Promise<Goal[]> {
  return unwrap(
    api.GET(GOALS_PATH, { params: { path: { organization_id: organizationId } } }),
  )
}

export function useGoals(organizationId: string) {
  return useQuery({
    queryKey: goalsKeys.list(organizationId),
    queryFn: () => fetchGoals(organizationId),
    enabled: Boolean(organizationId),
    retry: false,
    refetchOnWindowFocus: false,
  })
}

export function useCreateGoal(organizationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: GoalCreate) =>
      unwrap(
        api.POST(GOALS_PATH, {
          params: { path: { organization_id: organizationId } },
          body: payload,
        }),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: goalsKeys.list(organizationId) }),
  })
}

export function useUpdateGoal(organizationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ goalId, payload }: { goalId: string; payload: GoalUpdate }) =>
      unwrap(
        api.PATCH(GOAL_PATH, {
          params: { path: { organization_id: organizationId, goal_id: goalId } },
          body: payload,
        }),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: goalsKeys.list(organizationId) }),
  })
}

export function useDeleteGoal(organizationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (goalId: string) => {
      // 204 sans corps : `unwrap` ne convient pas, on contrôle le statut seul.
      const result = await api.DELETE(GOAL_PATH, {
        params: { path: { organization_id: organizationId, goal_id: goalId } },
      })
      if (!result.response.ok) {
        throw ApiError.from(result.response.status, result.error)
      }
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: goalsKeys.list(organizationId) }),
  })
}
