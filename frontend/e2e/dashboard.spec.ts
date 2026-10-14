// Tests e2e de la personnalisation du tableau de bord (sous-phase 6b-ii-b) :
// affichage piloté par la disposition servie par l'API, passage en mode
// personnalisation, déplacement d'un widget puis enregistrement (PUT), et remise
// à zéro (DELETE). Le backend étant absent, ses réponses sont simulées par
// `installApiMocks` (données fictives, AGENTS.md §5) ; les routes du Pouls et de
// la disposition sont surchargées ici pour fournir des widgets à déplacer.
import { expect, test, type Page } from '@playwright/test'
import { installApiMocks } from './helpers.ts'

const NOW = '2026-10-12T09:00:00Z'

/** Catalogue autorisé simulé (schéma DashboardWidgetOut). */
const CATALOG = [
  { widget_id: 'health', kind: 'health' },
  {
    widget_id: 'kpi.finance.revenue',
    kind: 'kpi',
    module: 'finance',
    metric_key: 'finance.revenue',
  },
  {
    widget_id: 'kpi.finance.margin',
    kind: 'kpi',
    module: 'finance',
    metric_key: 'finance.margin',
  },
  { widget_id: 'goals', kind: 'goals' },
  { widget_id: 'activity', kind: 'activity' },
]

/** Disposition par défaut simulée (schéma DashboardPlacement). */
const INITIAL_LAYOUT = [
  { widget_id: 'health', x: 0, y: 0, w: 12, h: 2 },
  { widget_id: 'kpi.finance.revenue', x: 0, y: 2, w: 4, h: 2 },
  { widget_id: 'kpi.finance.margin', x: 4, y: 2, w: 4, h: 2 },
  { widget_id: 'goals', x: 0, y: 4, w: 6, h: 6 },
  { widget_id: 'activity', x: 6, y: 4, w: 6, h: 6 },
]

interface Placement {
  widget_id: string
  x: number
  y: number
  w: number
  h: number
}

/** Écritures observées, renvoyées au test pour vérification. */
interface Recorded {
  put?: { widgets?: Placement[] }
  deletes: number
}

/** Surcharge les routes du Pouls et de la disposition avec des données riches. */
async function installDashboardMocks(page: Page): Promise<Recorded> {
  const recorded: Recorded = { deletes: 0 }

  await page.route('**/api/v1/organizations/*/pulse', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        kpis: [
          {
            module: 'finance',
            metric_key: 'finance.revenue',
            unit: 'EUR',
            value: 42100,
            previous_value: 40000,
            captured_at: NOW,
          },
          {
            module: 'finance',
            metric_key: 'finance.margin',
            unit: 'EUR',
            value: 12000,
            previous_value: 11000,
            captured_at: NOW,
          },
        ],
        health: { status: 'good', modules_with_data: 1, modules_total: 1 },
        activity: [],
      }),
    }),
  )

  // Pas de donnée sur la fenêtre : les cartes retombent sur la dernière valeur.
  await page.route('**/api/v1/organizations/*/metrics/*/comparison**', (route) =>
    route.fulfill({
      status: 404,
      contentType: 'application/problem+json',
      body: JSON.stringify({
        type: 'about:blank',
        title: 'Erreur',
        status: 404,
        detail: 'Aucune donnée sur la période.',
        instance: '',
      }),
    }),
  )

  await page.route('**/api/v1/organizations/*/dashboard', (route) => {
    const method = route.request().method()
    if (method === 'PUT') {
      recorded.put = route.request().postDataJSON() as { widgets?: Placement[] }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          available_widgets: CATALOG,
          layout: recorded.put.widgets ?? [],
          is_default: false,
        }),
      })
    }
    if (method === 'DELETE') {
      recorded.deletes += 1
      return route.fulfill({ status: 204 })
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        available_widgets: CATALOG,
        layout: INITIAL_LAYOUT,
        is_default: true,
      }),
    })
  })

  return recorded
}

test.describe('tableau de bord personnalisable', () => {
  test('affiche les widgets de la disposition servie par l’API', async ({ page }) => {
    await installApiMocks(page, { loggedIn: true })
    await installDashboardMocks(page)
    await page.goto('/')

    await expect(page.getByRole('heading', { name: "Vue d'ensemble" })).toBeVisible()
    await expect(page.locator('[data-widget-id="health"]')).toBeVisible()
    await expect(page.locator('[data-widget-id="kpi.finance.revenue"]')).toBeVisible()
    await expect(page.locator('[data-widget-id="kpi.finance.margin"]')).toBeVisible()
    await expect(page.locator('[data-widget-id="goals"]')).toBeVisible()
    await expect(page.locator('[data-widget-id="activity"]')).toBeVisible()

    // En lecture, aucun widget n'expose de poignée de déplacement.
    await expect(page.locator('.widget-handle')).toHaveCount(0)
  })

  test('déplace un widget, l’enregistre puis réinitialise', async ({ page }) => {
    await installApiMocks(page, { loggedIn: true })
    const recorded = await installDashboardMocks(page)
    await page.goto('/')

    await expect(page.locator('[data-widget-id="kpi.finance.revenue"]')).toBeVisible()
    await page.getByRole('button', { name: 'Personnaliser' }).click()

    // En mode personnalisation, chaque widget expose une poignée de déplacement.
    const handle = page.locator('[data-widget-id="kpi.finance.revenue"] .widget-handle')
    await expect(handle).toBeVisible()

    // Déplacement vers le bas : le widget change de ligne dans la grille.
    const box = await handle.boundingBox()
    expect(box).not.toBeNull()
    if (!box) throw new Error('Poignée de déplacement introuvable.')
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
    await page.mouse.down()
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2 + 260, { steps: 12 })
    await page.mouse.up()

    await page.getByRole('button', { name: 'Enregistrer' }).click()
    await expect(page.getByRole('button', { name: 'Personnaliser' })).toBeVisible()

    // Le corps du PUT reflète le déplacement : le KPI a descendu d'au moins une ligne.
    const saved = recorded.put?.widgets ?? []
    const moved = saved.find((widget) => widget.widget_id === 'kpi.finance.revenue')
    const original = INITIAL_LAYOUT.find((widget) => widget.widget_id === 'kpi.finance.revenue')
    expect(moved).toBeDefined()
    expect(original).toBeDefined()
    expect(moved!.y).toBeGreaterThan(original!.y)
    // La disposition reste complète : aucun widget perdu au passage.
    expect(saved).toHaveLength(INITIAL_LAYOUT.length)

    // Remise à zéro : la disposition personnelle est supprimée côté serveur.
    await page.getByRole('button', { name: 'Personnaliser' }).click()
    await page.getByRole('button', { name: 'Réinitialiser' }).click()
    await expect.poll(() => recorded.deletes).toBe(1)
  })
})
