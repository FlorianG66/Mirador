// Coquille de l'application : menu latéral gauche (SPEC §7) + barre supérieure
// + contenu de la route courante. Gère l'ouverture mobile (overlay, touche
// Échap) et le lien d'évitement vers le contenu (WCAG AA).
import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router'
import { useTranslation } from 'react-i18next'
import { Sidebar } from './Sidebar.tsx'
import { Topbar } from './Topbar.tsx'
import { PageTransition } from './PageTransition.tsx'

export function AppShell() {
  const { t } = useTranslation()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const closeSidebar = () => setSidebarOpen(false)

  useEffect(() => {
    if (!sidebarOpen) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setSidebarOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [sidebarOpen])

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[16rem_1fr]">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50 focus:rounded-md focus:bg-surface focus:px-3 focus:py-2 focus:text-sm focus:shadow-lg"
      >
        {t('common.skipToContent')}
      </a>

      <Sidebar open={sidebarOpen} onNavigate={closeSidebar} />

      {sidebarOpen ? (
        <div
          aria-hidden="true"
          onClick={closeSidebar}
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
        />
      ) : null}

      <div className="flex min-h-screen flex-col">
        <Topbar onOpenSidebar={() => setSidebarOpen(true)} />
        <main id="main-content" className="flex-1 p-4 lg:p-8">
          <PageTransition key={location.pathname}>
            <Outlet />
          </PageTransition>
        </main>
      </div>
    </div>
  )
}
