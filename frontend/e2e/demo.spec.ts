// e2e du mode démonstration (phase 7, SPEC §9) : le backend est absent, ses
// réponses sont simulées (données fictives, AGENTS.md §5). On vérifie le parcours
// public (choix du secteur → tableau de bord → bandeau) et le refus d'un lien
// expiré.
import { expect, test } from '@playwright/test'
import { installApiMocks } from './helpers.ts'

const SCENARIOS = [
  { key: 'restaurant', organization_name: 'Maison Fictive — Démo' },
  { key: 'agency', organization_name: 'Studio Fictif — Démo' },
  { key: 'ecommerce', organization_name: 'Boutique Fictive — Démo' },
]

test.describe('démonstration', () => {
  test('choisir un secteur ouvre une session fictive et affiche le bandeau', async ({
    page,
  }) => {
    const state = await installApiMocks(page)

    await page.route('**/api/v1/demo/scenarios', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(SCENARIOS),
      }),
    )
    await page.route('**/api/v1/demo/sessions', (route) => {
      state.loggedIn = true
      state.demo = true
      return route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          sector: 'restaurant',
          organization: { id: 'org-demo', name: 'Maison Fictive — Démo', is_demo: true },
        }),
      })
    })

    await page.goto('/demo')
    await expect(page.getByRole('heading', { name: 'Essayer la démo' })).toBeVisible()
    await expect(page.getByText('Maison Fictive — Démo')).toBeVisible()

    await page.getByRole('button', { name: /Restaurant/ }).click()
    await page.getByRole('button', { name: 'Ouvrir cette démo' }).click()

    await expect(page).toHaveURL('/')
    await expect(page.getByText('Mode démonstration')).toBeVisible()
    await expect(page.getByRole('link', { name: 'Créer mon compte' })).toBeVisible()
  })

  test('un lien expiré affiche un message et ne connecte pas', async ({ page }) => {
    await installApiMocks(page)

    await page.route('**/api/v1/demo/links/*', (route) =>
      route.fulfill({
        status: 410,
        contentType: 'application/problem+json',
        body: JSON.stringify({
          type: 'about:blank',
          title: 'Gone',
          status: 410,
          detail: 'Lien inconnu ou expiré.',
          instance: '/api/v1/demo/links',
        }),
      }),
    )

    await page.goto('/demo/jeton-expire')
    await expect(
      page.getByText('Ce lien de démonstration est inconnu ou a expiré.'),
    ).toBeVisible()
    await expect(page).toHaveURL('/demo/jeton-expire')
  })
})
