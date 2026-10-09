// Table des routes de la SPA. Extraite d'App.tsx pour être réutilisable dans
// les tests (createMemoryRouter) sans dépendre de l'historique du navigateur.
// L'AuthProvider enveloppe tout ; RequireAuth protège la coquille, puis chaque
// module est gardé par ses permissions (RequireModule) ou son rôle (RequireAdmin).
import type { RouteObject } from 'react-router'
import { AuthProvider } from '../auth/AuthProvider.tsx'
import { RequireAdmin, RequireAuth, RequireModule } from '../auth/guards.tsx'
import { AppShell } from '../components/layout/AppShell.tsx'
import { DashboardPage } from '../pages/DashboardPage.tsx'
import { ForgotPasswordPage } from '../pages/ForgotPasswordPage.tsx'
import { LoginPage } from '../pages/LoginPage.tsx'
import { ModulePage } from '../pages/ModulePage.tsx'
import { NotFoundPage } from '../pages/NotFoundPage.tsx'
import { RegisterPage } from '../pages/RegisterPage.tsx'
import { ResetPasswordPage } from '../pages/ResetPasswordPage.tsx'
import { TeamPage } from '../pages/TeamPage.tsx'

export const routes: RouteObject[] = [
  {
    element: <AuthProvider />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/register', element: <RegisterPage /> },
      { path: '/forgot-password', element: <ForgotPasswordPage /> },
      { path: '/reset-password', element: <ResetPasswordPage /> },
      {
        element: <RequireAuth />,
        children: [
          {
            path: '/',
            element: <AppShell />,
            children: [
              { index: true, element: <DashboardPage /> },
              {
                path: 'finance',
                element: (
                  <RequireModule moduleKey="finance">
                    <ModulePage moduleKey="finance" />
                  </RequireModule>
                ),
              },
              {
                path: 'web',
                element: (
                  <RequireModule moduleKey="web">
                    <ModulePage moduleKey="web" />
                  </RequireModule>
                ),
              },
              {
                path: 'social',
                element: (
                  <RequireModule moduleKey="social">
                    <ModulePage moduleKey="social" />
                  </RequireModule>
                ),
              },
              {
                path: 'projects',
                element: (
                  <RequireModule moduleKey="projects">
                    <ModulePage moduleKey="projects" />
                  </RequireModule>
                ),
              },
              {
                path: 'legal',
                element: (
                  <RequireModule moduleKey="legal">
                    <ModulePage moduleKey="legal" />
                  </RequireModule>
                ),
              },
              {
                path: 'team',
                element: (
                  <RequireAdmin>
                    <TeamPage />
                  </RequireAdmin>
                ),
              },
              { path: '*', element: <NotFoundPage /> },
            ],
          },
        ],
      },
    ],
  },
]
