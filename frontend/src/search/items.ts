// Index de la recherche globale (sous-phase 6b-i) : pages (vue d'ensemble,
// modules, équipe, paramètres) et KPI clés, restreints aux permissions de
// l'utilisateur courant. Aucune donnée d'API ni texte en dur : l'index est
// dérivé du catalogue statique de l'application (routes + KPI_META), les
// libellés sont traduits par l'appelant (AGENTS.md §7, §8).
import type { ModuleKey, MyPermissionsOut } from '../api/types.ts'
import { canSeeModule } from '../lib/permissions.ts'
import { KPI_META } from '../pulse/format.ts'

export interface SearchItem {
  id: string
  /** Libellé déjà traduit (nom de page ou de KPI). */
  label: string
  /** Ligne secondaire (module porteur d'un KPI) ; vide pour les pages. */
  hint: string
  /** Route vers laquelle naviguer. */
  to: string
}

/** Route de chaque module, utilisée par l'index et la palette. */
export const MODULE_ROUTES: Record<ModuleKey, string> = {
  finance: '/finance',
  web: '/web',
  social: '/social',
  projects: '/projects',
  legal: '/legal',
}

const MODULE_KEYS = Object.keys(MODULE_ROUTES) as ModuleKey[]

/**
 * Construit l'index de recherche pour un utilisateur : toutes les pages
 * accessibles puis les KPI clés des modules visibles (un KPI mène à son module).
 */
export function buildSearchItems(
  permissions: MyPermissionsOut | null,
  t: (key: string) => string,
): SearchItem[] {
  const items: SearchItem[] = [
    { id: 'page:dashboard', label: t('nav.dashboard'), hint: '', to: '/' },
  ]

  for (const moduleKey of MODULE_KEYS) {
    if (!canSeeModule(moduleKey, permissions)) continue
    items.push({
      id: `page:${moduleKey}`,
      label: t(`nav.${moduleKey}`),
      hint: '',
      to: MODULE_ROUTES[moduleKey],
    })
  }

  if (permissions?.role === 'admin') {
    items.push({ id: 'page:team', label: t('nav.team'), hint: '', to: '/team' })
  }
  items.push({ id: 'page:settings', label: t('nav.settings'), hint: '', to: '/settings' })

  for (const [metricKey, meta] of Object.entries(KPI_META)) {
    const moduleKey = metricKey.split('.')[0] as ModuleKey
    if (!canSeeModule(moduleKey, permissions)) continue
    items.push({
      id: `kpi:${metricKey}`,
      label: t(meta.labelKey),
      hint: t(`nav.${moduleKey}`),
      to: MODULE_ROUTES[moduleKey],
    })
  }

  return items
}

/** Minuscules, sans accents : la correspondance ignore la casse et les diacritiques. */
export function normalizeText(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase()
}

/**
 * Filtre l'index par une requête (sous-chaîne normalisée sur le libellé et la
 * ligne secondaire), dans l'ordre de `buildSearchItems`, borné à `limit`.
 */
export function searchItems(query: string, items: SearchItem[], limit = 8): SearchItem[] {
  const needle = normalizeText(query.trim())
  if (needle === '') return items.slice(0, limit)
  return items
    .filter((item) => normalizeText(`${item.label} ${item.hint}`).includes(needle))
    .slice(0, limit)
}
