// Tests de l'index de recherche (sous-phase 6b-i) : couverture des pages et des
// KPI selon les permissions, et filtrage de la requête (casse, accents, ligne
// secondaire). La clé i18n est renvoyée telle quelle : on teste la structure de
// l'index, pas les traductions (couvertes par le test de la palette).
import { describe, expect, it } from 'vitest'
import type { MyPermissionsOut } from '../api/types.ts'
import { buildSearchItems, normalizeText, searchItems, type SearchItem } from './items.ts'

const t = (key: string) => key

const admin: MyPermissionsOut = { role: 'admin', modules: {} }
const member = (modules: Record<string, 'view' | 'edit'>): MyPermissionsOut => ({
  role: 'member',
  modules,
})

describe('buildSearchItems', () => {
  it('couvre toutes les pages et les huit KPI pour un admin', () => {
    const items = buildSearchItems(admin, t)
    const ids = items.map((item) => item.id)
    expect(ids).toContain('page:dashboard')
    expect(ids).toContain('page:finance')
    expect(ids).toContain('page:web')
    expect(ids).toContain('page:social')
    expect(ids).toContain('page:projects')
    expect(ids).toContain('page:legal')
    expect(ids).toContain('page:team')
    expect(ids).toContain('page:settings')
    expect(items.filter((item) => item.id.startsWith('kpi:'))).toHaveLength(8)
  })

  it("restreint l'index au module visible pour un membre", () => {
    const items = buildSearchItems(member({ finance: 'view' }), t)
    const ids = items.map((item) => item.id)
    expect(ids).toContain('page:dashboard')
    expect(ids).toContain('page:finance')
    expect(ids).toContain('page:settings')
    expect(ids).not.toContain('page:web')
    expect(ids).not.toContain('page:team')
    // Seuls les KPI du module visible restent, dans l'ordre de KPI_META.
    const kpiIds = items
      .map((item) => item.id)
      .filter((id) => id.startsWith('kpi:'))
    expect(kpiIds).toEqual(['kpi:finance.revenue', 'kpi:finance.margin'])
    // La ligne secondaire d'un KPI indique son module porteur.
    expect(items.find((item) => item.id === 'kpi:finance.revenue')?.hint).toBe(
      'nav.finance',
    )
  })

  it('sans permissions ne propose que le tableau de bord et les paramètres', () => {
    const items = buildSearchItems(null, t)
    expect(items.map((item) => item.id)).toEqual(['page:dashboard', 'page:settings'])
  })
})

describe('searchItems', () => {
  const sample: SearchItem[] = [
    { id: 'p:finance', label: 'Finance', hint: '', to: '/finance' },
    { id: 'p:web', label: 'Web analytics', hint: '', to: '/web' },
    { id: 'k:revenue', label: "Chiffre d'affaires", hint: 'Finance', to: '/finance' },
  ]

  it('retourne l’index complet (borné) sans requête', () => {
    expect(searchItems('', sample)).toEqual(sample)
    expect(searchItems('', sample, 2)).toHaveLength(2)
  })

  it('filtre par sous-chaîne, insensible à la casse et aux accents', () => {
    expect(searchItems('WEB', sample).map((item) => item.id)).toEqual(['p:web'])
    expect(searchItems('chiffré', sample).map((item) => item.id)).toEqual(['k:revenue'])
  })

  it('cherche aussi dans la ligne secondaire (module porteur du KPI)', () => {
    expect(searchItems('finance', sample).map((item) => item.id)).toEqual([
      'p:finance',
      'k:revenue',
    ])
  })

  it('ne retourne rien quand aucun libellé ne correspond', () => {
    expect(searchItems('xyz', sample)).toEqual([])
  })
})

describe('normalizeText', () => {
  it('minimise la casse et retire les diacritiques', () => {
    expect(normalizeText('Éléphants à Paris')).toBe('elephants a paris')
  })
})
