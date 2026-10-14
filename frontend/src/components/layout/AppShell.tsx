// Coquille de l'application : rail de navigation gauche (SPEC §7) + barre
// supérieure + contenu de la route courante. Gère l'ouverture mobile (overlay,
// touche Échap) et le lien d'évitement vers le contenu (WCAG AA). La largeur du
// rail est exposée via --rail-w pour que le contenu s'y ajuste.
import type { CSSProperties } from 'react'
import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../../auth/context.ts'
import { useRailCollapsed } from '../../hooks/useRailCollapsed.ts'
import { SearchPalette } from '../../search/SearchPalette.tsx'
import { Sidebar } from './Sidebar.tsx'
import { Topbar } from './Topbar.tsx'
import { PageTransition } from './PageTransition.tsx'

const RAIL_EXPANDED = '16rem'
const RAIL_COLLAPSED = '4.75rem'

export function AppShell() {
  const { t } = useTranslation()
  const { permissions } = useAuth()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const { collapsed, toggle } = useRailCollapsed()

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
    <div
      className="min-h-screen"
      style={{ '--rail-w': collapsed ? RAIL_COLLAPSED : RAIL_EXPANDED } as CSSProperties}
    >
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50 focus:rounded-md focus:bg-surface focus:px-3 focus:py-2 focus:text-sm focus:shadow-raised print:hidden"
      >
        {t('common.skipToContent')}
      </a>

      <Sidebar
        open={sidebarOpen}
        onNavigate={closeSidebar}
        collapsed={collapsed}
        onToggleCollapsed={toggle}
      />

      {sidebarOpen ? (
        <div
          aria-hidden="true"
          onClick={closeSidebar}
          className="fixed inset-0 z-30 bg-black/40 lg:hidden print:hidden"
        />
      ) : null}

      <div className="flex min-h-screen flex-col transition-[padding] duration-200 lg:pl-[var(--rail-w)] print:pl-0">
        <Topbar
          onOpenSidebar={() => setSidebarOpen(true)}
          onOpenSearch={() => setSearchOpen(true)}
        />
        <main id="main-content" className="flex-1 p-4 lg:p-8 print:p-0">
          <PageTransition key={location.pathname}>
            <Outlet />
          </PageTransition>
        </main>
      </div>

      <SearchPalette
        open={searchOpen}
        onOpen={() => setSearchOpen(true)}
        onClose={() => setSearchOpen(false)}
        permissions={permissions}
      />
    </div>
  )
}
