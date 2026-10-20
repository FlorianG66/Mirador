// Logique de mise en page du tableau de bord (sous-phase 6b-ii-b). Ce module ne
// contient que des fonctions pures : conversion entre la disposition servie par
// l'API (widget_id + x/y/w/h) et le format attendu par react-grid-layout (items
// `i`), géométrie de la grille et libellé des widgets. Aucun rendu ici.
import type { Layout } from 'react-grid-layout'
import type { DashboardPlacement, DashboardWidget } from '../api/types.ts'
import { KPI_META } from '../pulse/format.ts'

// Nombre de colonnes de la grille : doit rester aligné sur le backend
// (GRID_COLUMNS, app/schemas/dashboard.py), qui valide x + w.
export const GRID_COLUMNS = 12
// Hauteur d'une unité de ligne en pixels : un widget de hauteur h mesure h × ce
// pas. Le pas est volontairement fin pour que le redimensionnement soit souple.
export const ROW_HEIGHT = 40
// Gouttière [horizontale, verticale] entre widgets, en pixels.
export const GRID_MARGIN: readonly [number, number] = [16, 16]
// Bornes de taille d'un widget : alignées sur la validation du backend.
export const MIN_WIDGET_WIDTH = 2
export const MIN_WIDGET_HEIGHT = 2
export const MAX_WIDGET_HEIGHT = 24

/** Convertit la disposition de l'API en layout react-grid-layout. */
export function toGridLayout(placements: DashboardPlacement[]): Layout {
  return placements.map((placement) => ({
    i: placement.widget_id,
    x: placement.x,
    y: placement.y,
    w: placement.w,
    h: placement.h,
    minW: MIN_WIDGET_WIDTH,
    minH: MIN_WIDGET_HEIGHT,
    maxW: GRID_COLUMNS,
    maxH: MAX_WIDGET_HEIGHT,
  }))
}

/**
 * Convertit un layout react-grid-layout en placements pour l'API. L'ordre est
 * stable (tri par ligne puis colonne) pour que le corps du PUT soit déterministe.
 */
export function toPlacements(layout: Layout): DashboardPlacement[] {
  return [...layout]
    .sort((a, b) => a.y - b.y || a.x - b.x)
    .map((item) => ({
      widget_id: item.i,
      x: item.x,
      y: item.y,
      w: item.w,
      h: item.h,
    }))
}

/**
 * Deux dispositions sont-elles identiques ? La comparaison se fait par
 * identifiant de widget, car react-grid-layout peut réordonner le tableau. Sert
 * à ignorer les rappels de layout sans changement réel (évite les boucles).
 */
export function sameLayout(a: Layout, b: Layout): boolean {
  if (a.length !== b.length) return false
  const byId = new Map(b.map((item) => [item.i, item]))
  return a.every((item) => {
    const other = byId.get(item.i)
    return (
      other !== undefined &&
      item.x === other.x &&
      item.y === other.y &&
      item.w === other.w &&
      item.h === other.h
    )
  })
}

/** Clé i18n du titre d'un widget : le backend ne fournit aucun libellé. */
export function widgetTitleKey(widget: DashboardWidget): string {
  if (widget.kind === 'kpi' && widget.metric_key) {
    return KPI_META[widget.metric_key]?.labelKey ?? widget.metric_key
  }
  if (widget.kind === 'health') return 'dashboard.healthTitle'
  if (widget.kind === 'goals') return 'goals.title'
  if (widget.kind === 'activity') return 'dashboard.activityTitle'
  return widget.widget_id
}
