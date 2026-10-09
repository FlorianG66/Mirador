// Setup des tests Vitest : matchers jest-dom, instance i18n partagée (FR par
// défaut) et nettoyage du DOM entre tests.
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'
import '../i18n/index.ts'

afterEach(() => {
  cleanup()
})
