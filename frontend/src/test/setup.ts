// Setup des tests Vitest : matchers jest-dom, instance i18n partagée (FR par
// défaut) et nettoyage du DOM entre tests.
import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { afterEach, vi } from 'vitest'
import '../i18n/index.ts'

// Les pages à graphiques (Recharts) sont lentes à rendre sous jsdom. Le délai
// par défaut de 1 s des requêtes asynchrones (`findBy*`) est trop court dès que
// la suite tourne en parallèle : on le porte à 5 s pour éviter des échecs
// intermittents sans données réelles.
configure({ asyncUtilTimeout: 5000 })

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})
