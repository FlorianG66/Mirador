// Tests e2e du parcours de connexion (sous-phase 3d-c, ROADMAP phase 3) :
// le backend étant absent de l'environnement de test, ses réponses sont
// simulées par `installApiMocks` (données fictives, AGENTS.md §5).
import { expect, test } from '@playwright/test'
import { installApiMocks } from './helpers.ts'

test.describe('connexion', () => {
  test('identifiants valides : arrivée sur le tableau de bord', async ({ page }) => {
    const state = await installApiMocks(page)

    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'Connexion' })).toBeVisible()

    await page.getByLabel('Adresse e-mail').fill('admin@example.com')
    await page.getByLabel('Mot de passe').fill('mot-de-passe-valide')
    await page.getByRole('button', { name: 'Se connecter' }).click()

    await expect(page).toHaveURL('/')
    await expect(page.getByRole('heading', { name: "Vue d'ensemble" })).toBeVisible()
    expect(state.loggedIn).toBe(true)
  })

  test('identifiants incorrects : message d’erreur, pas de navigation', async ({ page }) => {
    await installApiMocks(page, { loginRejected: true })

    await page.goto('/login')
    await page.getByLabel('Adresse e-mail').fill('admin@example.com')
    await page.getByLabel('Mot de passe').fill('mauvais-mot-de-passe')
    await page.getByRole('button', { name: 'Se connecter' }).click()

    await expect(page.getByRole('alert')).toContainText('Identifiants incorrects')
    await expect(page).toHaveURL('/login')
  })

  test('compte à A2F : redirection vers le défi 2FA', async ({ page }) => {
    await installApiMocks(page, { twoFactorRequired: true })

    await page.goto('/login')
    await page.getByLabel('Adresse e-mail').fill('admin@example.com')
    await page.getByLabel('Mot de passe').fill('mot-de-passe-valide')
    await page.getByRole('button', { name: 'Se connecter' }).click()

    await expect(page).toHaveURL('/2fa')
    await expect(
      page.getByRole('heading', { name: 'Double authentification' }),
    ).toBeVisible()
  })
})
