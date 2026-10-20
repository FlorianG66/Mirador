// Tests des fonctions pures de mise en page (sous-phase 6b-ii-b) : conversion
// entre la disposition de l'API et le layout react-grid-layout, comparaison de
// dispositions et clé i18n du titre d'un widget. Aucun rendu ici.
import { describe, expect, it } from 'vitest'
import type { DashboardPlacement, DashboardWidget } from '../api/types.ts'
import { sameLayout, toGridLayout, toPlacements, widgetTitleKey } from './layout.ts'

function placement(overrides: Partial<DashboardPlacement> = {}): DashboardPlacement {
  return { widget_id: 'health', x: 0, y: 0, w: 12, h: 2, ...overrides }
}

describe('toGridLayout', () => {
  it('renomme widget_id en i et borne la taille des widgets', () => {
    const layout = toGridLayout([placement({ widget_id: 'kpi.finance.revenue', x: 4, y: 2 })])
    expect(layout).toHaveLength(1)
    expect(layout[0]).toMatchObject({ i: 'kpi.finance.revenue', x: 4, y: 2, w: 12, h: 2 })
    expect(layout[0].minW).toBeGreaterThan(0)
    expect(layout[0].maxW).toBeGreaterThan(0)
    expect(layout[0].maxH).toBeGreaterThan(0)
  })
})

describe('toPlacements', () => {
  it('renomme i en widget_id et ne garde que les champs de l’API', () => {
    const placements = toPlacements([
      { i: 'goals', x: 0, y: 4, w: 6, h: 6, minW: 2, minH: 2, maxW: 12, maxH: 24 },
    ])
    expect(placements).toEqual([{ widget_id: 'goals', x: 0, y: 4, w: 6, h: 6 }])
  })

  it('trie par ligne puis colonne pour un corps de requête déterministe', () => {
    const placements = toPlacements([
      { i: 'c', x: 4, y: 2, w: 4, h: 2 },
      { i: 'b', x: 0, y: 2, w: 4, h: 2 },
      { i: 'a', x: 0, y: 0, w: 12, h: 2 },
    ])
    expect(placements.map((item) => item.widget_id)).toEqual(['a', 'b', 'c'])
  })
})

describe('sameLayout', () => {
  const base = [
    { i: 'health', x: 0, y: 0, w: 12, h: 2 },
    { i: 'goals', x: 0, y: 4, w: 6, h: 6 },
  ]

  it('ignore l’ordre du tableau', () => {
    expect(sameLayout(base, [base[1], base[0]])).toBe(true)
  })

  it('ignore les champs internes (moved) mais pas la géométrie', () => {
    const moved = [
      { ...base[0], moved: true },
      { ...base[1] },
    ]
    expect(sameLayout(base, moved)).toBe(true)
    expect(sameLayout(base, [{ ...base[0], w: 6 }, base[1]])).toBe(false)
  })

  it('détecte une différence de nombre d’éléments ou d’identifiant', () => {
    expect(sameLayout(base, [base[0]])).toBe(false)
    expect(sameLayout(base, [{ ...base[0], i: 'other' }, base[1]])).toBe(false)
  })
})

describe('widgetTitleKey', () => {
  it('renvoie la clé du KPI pour un widget KPI', () => {
    const widget: DashboardWidget = {
      widget_id: 'kpi.finance.revenue',
      kind: 'kpi',
      module: 'finance',
      metric_key: 'finance.revenue',
    }
    expect(widgetTitleKey(widget)).toBe('finance.kpiRevenue')
  })

  it('renvoie une clé dédiée pour les widgets non-KPI', () => {
    expect(widgetTitleKey({ widget_id: 'health', kind: 'health' })).toBe('dashboard.healthTitle')
    expect(widgetTitleKey({ widget_id: 'goals', kind: 'goals' })).toBe('goals.title')
    expect(widgetTitleKey({ widget_id: 'activity', kind: 'activity' })).toBe(
      'dashboard.activityTitle',
    )
  })
})
