// Panneau projets & tâches (sous-phase 5d, SPEC §3) : les 10 séries canoniques
// chargées ensemble, avec polling 5 minutes. Une série absente du registre (404)
// compte comme « pas encore connectée » ; toute autre erreur remonte à la page.
// Même patron que `finance.ts` / `web.ts` / `social.ts`.
import { useQuery } from '@tanstack/react-query'
import type { MetricSeries, ProjectMetricKey } from '../api/types'
import {
  DEFAULT_LIMIT,
  POLLING_INTERVAL_MS,
  fetchMetricSeries,
  isNotFound,
  metricsKeys,
} from './queries.ts'

export const PROJECT_METRIC_KEYS: ProjectMetricKey[] = [
  'projects.tasks_done',
  'projects.tasks_created',
  'projects.open_tasks',
  'projects.overdue_tasks',
  'projects.avg_completion_time',
  'projects.avg_progress',
  'projects.active_projects',
  'projects.tasks_by_status',
  'projects.person_load',
  'projects.upcoming_milestones',
]

export interface ProjectsPanel {
  /** Les séries présentes (limitées aux points chargés par le serveur). */
  series: Partial<Record<ProjectMetricKey, MetricSeries>>
  /** Les séries sans donnée (404 pour l'organisation active). */
  missing: ProjectMetricKey[]
}

export async function fetchProjectsPanel(
  organizationId: string,
  limit = DEFAULT_LIMIT,
): Promise<ProjectsPanel> {
  const results = await Promise.all(
    PROJECT_METRIC_KEYS.map(async (key) => {
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

  const series: ProjectsPanel['series'] = {}
  const missing: ProjectMetricKey[] = []
  for (const [key, value] of results) {
    if (value === null) {
      missing.push(key)
    } else {
      series[key] = value
    }
  }
  return { series, missing }
}

export function useProjectsPanel(organizationId: string, limit = DEFAULT_LIMIT) {
  return useQuery({
    queryKey: metricsKeys.panel(organizationId, 'projects'),
    queryFn: () => fetchProjectsPanel(organizationId, limit),
    // Polling toutes les 5 min : les données se rafraîchissent sans geste.
    refetchInterval: POLLING_INTERVAL_MS,
    retry: false,
    refetchOnWindowFocus: false,
  })
}
