// Tests e2e du centre de notifications (sous-phase 6c-ii) : compteur de non-lus
// dans la barre supérieure, ouverture du panneau, contenu traduit, « tout
// marquer comme lu », navigation vers le module et fermeture par Échap. Le
// backend étant absent, ses réponses sont simulées par `installApiMocks`
// (données fictives, AGENTS.md §5).
import { expect, test } from '@playwright/test'
import { installApiMocks } from './helpers.ts'

test.describe('centre de notifications', () => {
  test('affiche les non-lus et les marque tous comme lus', async ({ page }) => {
    await installApiMocks(page, { loggedIn: true })
    await page.goto('/')
    await expect(page.getByRole('heading', { name: "Vue d'ensemble" })).toBeVisible()

    await expect(page.getByTestId('notifications-badge')).toHaveText('1')

    await page.getByRole('button', { name: /Notifications/ }).click()
    const panel = page.getByRole('dialog', { name: 'Notifications' })
    await expect(panel).toBeVisible()
    await expect(panel.getByText('Objectif atteint')).toBeVisible()
    await expect(panel.getByText(/Chiffre d'affaires/)).toBeVisible()

    await panel.getByRole('button', { name: 'Tout marquer comme lu' }).click()
    await expect(page.getByTestId('notifications-badge')).toHaveCount(0)
  })

  test('navigue vers le module au clic et se ferme par Échap', async ({ page }) => {
    await installApiMocks(page, { loggedIn: true })
    await page.goto('/')
    await expect(page.getByRole('heading', { name: "Vue d'ensemble" })).toBeVisible()

    const bell = page.getByRole('button', { name: /Notifications/ })
    await bell.click()
    const panel = page.getByRole('dialog', { name: 'Notifications' })
    await expect(panel).toBeVisible()

    await page.keyboard.press('Escape')
    await expect(panel).toBeHidden()

    await bell.click()
    await panel.getByRole('link', { name: /Objectif atteint/ }).click()
    await expect(page).toHaveURL(/\/finance$/)
  })
})
