// Configuration Playwright (sous-phase 3d-c) : les tests e2e lancent le serveur
// Vite de dev et pilote Edge installé sur la machine (channel msedge, pas de
// téléchargement de Chromium). Le backend FastAPI est volontairement absent :
// les appels /api/v1 sont interceptés route à route (mocks fictifs, AGENTS.md §5).
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    channel: 'msedge',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
})
