// Table des routes de la SPA. Extraite d'App.tsx pour être réutilisable dans
// les tests (createMemoryRouter) sans dépendre de l'historique du navigateur.
// L'AuthProvider enveloppe tout ; RequireAuth protège la coquille, puis chaque
// module est gardé par ses permissions (RequireModule) ou son rôle (RequireAdmin).
import type { RouteObject } from 'react-router'
import { AuthProvider } from '../auth/AuthProvider.tsx'
import { RequireAdmin, RequireAuth, RequireModule } from '../auth/guards.tsx'
import { AppShell } from '../components/layout/AppShell.tsx'
import { DashboardPage } from '../pages/DashboardPage.tsx'
import { FinancePage } from '../pages/FinancePage.tsx'
import { ForgotPasswordPage } from '../pages/ForgotPasswordPage.tsx'
import { LoginPage } from '../pages/LoginPage.tsx'
import { ModulePage } from '../pages/ModulePage.tsx'
import { NotFoundPage } from '../pages/NotFoundPage.tsx'
import { ProjectsPage } from '../pages/ProjectsPage.tsx'
import { RegisterPage } from '../pages/RegisterPage.tsx'
import { SettingsPage } from '../pages/SettingsPage.tsx'
import { ResetPasswordPage } from '../pages/ResetPasswordPage.tsx'
import { SocialPage } from '../pages/SocialPage.tsx'
import { TeamPage } from '../pages/TeamPage.tsx'
import { TwoFactorPage } from '../pages/TwoFactorPage.tsx'
import { WebPage } from '../pages/WebPage.tsx'

export const routes: RouteObject[] = [
  {
    element: <AuthProvider />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/register', element: <RegisterPage /> },
      { path: '/forgot-password', element: <ForgotPasswordPage /> },
      { path: '/reset-password', element: <ResetPasswordPage /> },
      { path: '/2fa', element: <TwoFactorPage /> },
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
                    <FinancePage />
                  </RequireModule>
                ),
              },
              {
                path: 'web',
                element: (
                  <RequireModule moduleKey="web">
                    <WebPage />
                  </RequireModule>
                ),
              },
              {
                path: 'social',
                element: (
                  <RequireModule moduleKey="social">
                    <SocialPage />
                  </RequireModule>
                ),
              },
              {
                path: 'projects',
                element: (
                  <RequireModule moduleKey="projects">
                    <ProjectsPage />
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
                path: 'settings',
                element: <SettingsPage />,
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
