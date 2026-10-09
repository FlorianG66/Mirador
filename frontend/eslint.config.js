import js from '@eslint/js'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import globals from 'globals'
import tseslint from 'typescript-eslint'

// Configuration ESLint flat du frontend : base recommandée JS + TypeScript
// (typé), règles React Hooks explicites (les bundles de config du plugin
// changent de clé entre versions — on épingle les règles par nom) et
// react-refresh pour le mode dev.
export default tseslint.config(
  // `schema.d.ts` est g�n�r� depuis l'OpenAPI : on ne le lint pas.
  { ignores: ['dist', 'src/api/schema.d.ts'] },
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      ...tseslint.configs.recommended,
      tseslint.configs.stylistic,
    ],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
    },
  },
)
