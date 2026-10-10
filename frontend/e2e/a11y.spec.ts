// Vérification a11y de base (sous-phase 3d-c, ROADMAP phase 3 « vérification
// a11y de base ») : scan axe-core des pages clés. Le seuil retenu — aucune
// violation de niveau serious ou critical (équivalent WCAG AA) — est volontaire
// pour laisser passer les améliorations progressives dans les phases suivantes.
// L'audit s'exécute en prefers-reduced-motion : reduce pour mesurer l'état final
// (les fondus d'apparition du PageTransition fausseraient le contraste mesuré)
// et, au passage, vérifie le respect de la réduction des animations (SPEC §7).
import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { installApiMocks } from './helpers.ts'

test.use({ contextOptions: { reducedMotion: 'reduce' } })

async function expectNoSeriousViolations(page: Page): Promise<void> {
  const results = await new AxeBuilder({ page }).analyze()
  const notable = results.violations.filter(
    (violation) => violation.impact === 'serious' || violation.impact === 'critical',
  )
  const summary = notable
    .map((violation) => `${violation.id} (${violation.impact}) : ${violation.help}`)
    .join('\n')
  expect(notable, summary || 'aucune violation series/signalee').toEqual([])
}

test('a11y : page de connexion sans violation sérieuse', async ({ page }) => {
  await installApiMocks(page)
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: 'Connexion' })).toBeVisible()
  await expectNoSeriousViolations(page)
})

test('a11y : tableau de bord authentifié sans violation sérieuse', async ({ page }) => {
  await installApiMocks(page, { loggedIn: true })
  await page.goto('/')
  await expect(
    page.getByRole('heading', { name: 'Bienvenue sur votre tableau de bord' }),
  ).toBeVisible()
  await expectNoSeriousViolations(page)
})
