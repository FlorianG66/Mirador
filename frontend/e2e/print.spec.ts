// Tests e2e de l'export PDF (sous-phase 6c-i). Le bouton d'export doit être
// présent à l'écran, et à l'impression (émulation du média « print »)
// l'interface doit disparaître au profit du seul document : rail et boutons
// masqués, bandeau de génération affiché, titre de page conservé. Backend absent
// → réponses simulées par `installApiMocks` (données fictives, AGENTS.md §5).
import { expect, test } from '@playwright/test'
import { installApiMocks } from './helpers.ts'

test.describe('export PDF', () => {
  test('n’imprime que le document, pas l’interface', async ({ page }) => {
    await installApiMocks(page, { loggedIn: true })
    await page.goto('/')

    const heading = page.getByRole('heading', { name: "Vue d'ensemble" })
    // Localisateurs indépendants de la visibilité : ils doivent continuer à
    // désigner le nœud une fois celui-ci masqué par l'impression.
    const exportButton = page.locator('button:has-text("Exporter en PDF")')
    const sidebar = page.locator('aside')

    await expect(heading).toBeVisible()
    await expect(exportButton).toBeVisible()
    await expect(sidebar).toBeVisible()

    await page.emulateMedia({ media: 'print' })

    await expect(sidebar).toBeHidden()
    await expect(exportButton).toBeHidden()
    await expect(page.getByText(/Document généré le/)).toBeVisible()
    // Le titre reste l'en-tête du document imprimé.
    await expect(heading).toBeVisible()

    await page.emulateMedia({ media: 'screen' })
    await expect(exportButton).toBeVisible()
  })
})
