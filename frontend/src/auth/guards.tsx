// Gardes de routes (phase 3c). `RequireAuth` bloque tant que l'état d'auth n'est
// pas résolu, `RequireModule` exige une permission de lecture sur un module (un
// admin a tous les droits), `RequireAdmin` est réservé au rôle admin. Un niveau
// `none` renvoie la page 403 plutôt qu'une redirection, pour ne pas boucler.
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, Outlet, useLocation } from 'react-router'
import type { ModuleKey } from '../api/types.ts'
import { ErrorState } from '../components/ui/ErrorState.tsx'
import { ForbiddenPage } from '../pages/ForbiddenPage.tsx'
import { useAuth } from './context.ts'

function LoadingBlock() {
  const { t } = useTranslation()
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <p role="status" className="text-sm text-muted">
        {t('common.loading')}
      </p>
    </div>
  )
}

// Résout les cas communs (chargement, visiteur, erreur rechargeable) puis rend
// les enfants une fois la session authentifiée.
function AuthGate({ children }: { children: ReactNode }) {
  const { status, reload } = useAuth()
  const { t } = useTranslation()
  const location = useLocation()

  if (status === 'loading') {
    return <LoadingBlock />
  }
  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  if (status === 'error') {
    return (
      <ErrorState
        title={t('errorState.title')}
        description={t('errorState.description')}
        retryLabel={t('common.retry')}
        onRetry={() => void reload()}
      />
    )
  }
  return <>{children}</>
}

function ModuleGate({ moduleKey, children }: { moduleKey: ModuleKey; children: ReactNode }) {
  const { permissions } = useAuth()

  if (!permissions) {
    return <ForbiddenPage />
  }
  const level = permissions.role === 'admin' ? 'edit' : (permissions.modules[moduleKey] ?? 'none')
  if (level === 'none') {
    return <ForbiddenPage />
  }
  return <>{children}</>
}

function AdminGate({ children }: { children: ReactNode }) {
  const { permissions } = useAuth()

  if (permissions?.role !== 'admin') {
    return <ForbiddenPage />
  }
  return <>{children}</>
}

export function RequireAuth() {
  return (
    <AuthGate>
      <Outlet />
    </AuthGate>
  )
}

export interface RequireModuleProps {
  moduleKey: ModuleKey
  children: ReactNode
}

export function RequireModule({ moduleKey, children }: RequireModuleProps) {
  return (
    <AuthGate>
      <ModuleGate moduleKey={moduleKey}>{children}</ModuleGate>
    </AuthGate>
  )
}

export function RequireAdmin({ children }: { children: ReactNode }) {
  return (
    <AuthGate>
      <AdminGate>{children}</AdminGate>
    </AuthGate>
  )
}
