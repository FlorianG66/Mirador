// Table des routes de la SPA. Extraite d'App.tsx pour être réutilisable dans
// les tests (createMemoryRouter) sans dépendre de l'historique du navigateur.
import type { RouteObject } from 'react-router'
import { AppShell } from '../components/layout/AppShell.tsx'
import { DashboardPage } from '../pages/DashboardPage.tsx'
import { ModulePage } from '../pages/ModulePage.tsx'
import { NotFoundPage } from '../pages/NotFoundPage.tsx'

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'finance', element: <ModulePage moduleKey="finance" /> },
      { path: 'analytics', element: <ModulePage moduleKey="analytics" /> },
      { path: 'social', element: <ModulePage moduleKey="social" /> },
      { path: 'projects', element: <ModulePage moduleKey="projects" /> },
      { path: 'legal', element: <ModulePage moduleKey="legal" /> },
      { path: 'team', element: <ModulePage moduleKey="team" /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]
