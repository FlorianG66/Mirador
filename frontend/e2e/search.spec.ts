// Tests e2e de la recherche globale (sous-phase 6b-i) : raccourci Ctrl+K et
// bouton de la barre supérieure, filtrage des résultats, fermeture par Échap.
// Le backend étant absent, ses réponses sont simulées par `installApiMocks`
// (données fictives, AGENTS.md §5) ; la recherche n'appelle d'ailleurs aucune
// API : son index est dérivé du catalogue statique de l'application.
import { expect, test } from '@playwright/test'
import { installApiMocks } from './helpers.ts'

test.describe('recherche globale', () => {
  test('s’ouvre par Ctrl+K, filtre les résultats et se ferme par Échap', async ({ page }) => {
    await installApiMocks(page, { loggedIn: true })
    await page.goto('/')
    await expect(page.getByRole('heading', { name: "Vue d'ensemble" })).toBeVisible()

    await page.keyboard.press('Control+k')
    const palette = page.getByRole('dialog', { name: 'Recherche globale' })
    await expect(palette).toBeVisible()

    await palette.getByRole('combobox').fill('finance')
    await expect(palette.getByRole('option', { name: /Finance/ }).first()).toBeVisible()

    await page.keyboard.press('Escape')
    await expect(palette).not.toBeVisible()
  })

  test('s’ouvre depuis le bouton de la barre supérieure', async ({ page }) => {
    await installApiMocks(page, { loggedIn: true })
    await page.goto('/')

    await page.getByRole('button', { name: 'Rechercher' }).click()
    await expect(page.getByRole('dialog', { name: 'Recherche globale' })).toBeVisible()
  })
})
