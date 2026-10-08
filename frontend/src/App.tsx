// Écran provisoire de la sous-phase 3a : vérifie que la chaîne React +
// TypeScript strict + ESLint + Vitest tourne. Le vrai layout (menu latéral,
// design tokens, i18n) arrive en 3b/3c.
import { PROJECT_NAME } from './constants.ts'

export default function App() {
  return (
    <main>
      <h1>{PROJECT_NAME}</h1>
      <p>Application en construction — sous-phase 3a (socle frontend).</p>
    </main>
  )
}
