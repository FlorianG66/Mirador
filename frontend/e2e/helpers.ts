// Aide aux tests e2e (sous-phase 3d-c) : intercepter les routes /api/v1 du
// backend, volontairement absent, avec des réponses fictives (jamais de vraies
// données dans ce dépôt public, AGENTS.md §5). L'état (connecté ou non, A2F
// exigée ou non) est piloté par un objet mutable que chaque test configure.
import type { Page, Route } from '@playwright/test'

export const ORG_ID = '11111111-1111-4111-8111-111111111111'
export const USER_ID = '22222222-2222-4222-8222-222222222222'

export interface ApiMockState {
  /** Si `true`, `/auth/me` renvoie une session complète. */
  loggedIn: boolean
  /** Si `true`, `/auth/login` répond `totp_required: true`. */
  twoFactorRequired: boolean
  /** Si `true`, `/auth/login` répond 401 (identifiants incorrects). */
  loginRejected: boolean
}

function fulfill(route: Route, status: number, body: unknown): Promise<void> {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

function problem(status: number, detail: string): unknown {
  return { type: 'about:blank', title: 'Erreur', status, detail, instance: '' }
}

const memberships = [{ organization_id: ORG_ID, role: 'admin' }]
const modules = {
  finance: 'edit',
  web: 'edit',
  social: 'edit',
  projects: 'edit',
  legal: 'edit',
}

/** Installe les mocks API sur une page et renvoie l'état pilotable. */
export async function installApiMocks(
  page: Page,
  overrides: Partial<ApiMockState> = {},
): Promise<ApiMockState> {
  const state: ApiMockState = {
    loggedIn: false,
    twoFactorRequired: false,
    loginRejected: false,
    ...overrides,
  }

  await page.route('**/api/v1/auth/me', (route) =>
    state.loggedIn
      ? fulfill(route, 200, { id: USER_ID, email: 'admin@example.com', memberships })
      : fulfill(route, 401, problem(401, 'Non authentifié.')),
  )

  await page.route('**/api/v1/auth/login', (route) => {
    if (state.loginRejected) {
      return fulfill(route, 401, problem(401, 'Identifiants incorrects.'))
    }
    if (state.twoFactorRequired) {
      return fulfill(route, 200, { user: null, totp_required: true })
    }
    state.loggedIn = true
    return fulfill(route, 200, {
      user: { id: USER_ID, email: 'admin@example.com' },
      totp_required: false,
    })
  })

  await page.route('**/api/v1/organizations/*/permissions', (route) =>
    fulfill(route, 200, { role: 'admin', modules }),
  )

  await page.route('**/api/v1/organizations/*/pulse', (route) =>
    fulfill(route, 200, {
      kpis: [],
      health: { status: 'unknown', modules_with_data: 0, modules_total: 0 },
      activity: [],
    }),
  )

  // Catalogue et disposition par défaut, cohérents avec un Pouls vide (le
  // backend écarte l'activité pour un non-admin, pas ici : session admin).
  await page.route('**/api/v1/organizations/*/dashboard', (route) =>
    fulfill(route, 200, {
      available_widgets: [
        { widget_id: 'health', kind: 'health' },
        { widget_id: 'goals', kind: 'goals' },
        { widget_id: 'activity', kind: 'activity' },
      ],
      layout: [
        { widget_id: 'health', x: 0, y: 0, w: 12, h: 2 },
        { widget_id: 'goals', x: 0, y: 2, w: 6, h: 6 },
        { widget_id: 'activity', x: 6, y: 2, w: 6, h: 6 },
      ],
      is_default: true,
    }),
  )

  await page.route('**/api/v1/organizations/*/goals', (route) => fulfill(route, 200, []))

  return state
}
