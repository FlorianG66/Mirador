// Barre supérieure : ouverture du menu (mobile), fil d'ariane, puis langue,
// thème et identité de l'utilisateur. Collée en haut (sticky) et translucide
// pour laisser deviner le contenu qui défile dessous.
import { ChevronRight, Menu, Search } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router'
import { useAuth } from '../../auth/context.ts'
import { PROJECT_NAME } from '../../constants.ts'
import { NotificationBell } from '../../notifications/NotificationBell.tsx'
import { LanguageSwitcher } from './LanguageSwitcher.tsx'
import { ThemeToggle } from './ThemeToggle.tsx'

export interface TopbarProps {
  onOpenSidebar: () => void
  onOpenSearch: () => void
}

// Libellés du fil d'ariane par route (i18n). Toute route inconnue retombe sur le
// nom du projet.
const CRUMB_KEYS: Record<string, string> = {
  '/': 'nav.dashboard',
  '/finance': 'nav.finance',
  '/web': 'nav.web',
  '/social': 'nav.social',
  '/projects': 'nav.projects',
  '/legal': 'nav.legal',
  '/team': 'nav.team',
}

export function Topbar({ onOpenSidebar, onOpenSearch }: TopbarProps) {
  const { t } = useTranslation()
  const { user, permissions } = useAuth()
  const location = useLocation()

  const crumbKey = CRUMB_KEYS[location.pathname]
  const email = user?.email ?? ''
  const roleLabel =
    permissions?.role === 'admin' ? t('topbar.roleAdmin') : t('topbar.roleMember')

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border bg-background/80 px-4 backdrop-blur lg:px-6 print:hidden">
      <button
        type="button"
        onClick={onOpenSidebar}
        aria-label={t('common.openMenu')}
        className="inline-flex size-9 items-center justify-center rounded-md text-muted transition-colors hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand lg:hidden"
      >
        <Menu aria-hidden="true" className="size-5" />
      </button>

      <nav aria-label={t('topbar.breadcrumbAria')} className="flex min-w-0 items-center gap-1.5 text-sm">
        <span className="hidden text-muted sm:inline">{PROJECT_NAME}</span>
        <ChevronRight aria-hidden="true" className="hidden size-4 text-muted sm:inline" />
        <span className="truncate font-medium text-foreground">
          {crumbKey ? t(crumbKey) : PROJECT_NAME}
        </span>
      </nav>

      <div className="flex-1" />

      <button
        type="button"
        onClick={onOpenSearch}
        aria-label={t('search.open')}
        className="inline-flex h-9 items-center gap-2 rounded-md border border-border bg-surface px-2.5 text-sm text-muted transition-colors hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
      >
        <Search aria-hidden="true" className="size-4" />
        <span className="hidden lg:inline">{t('search.open')}</span>
        <kbd className="hidden rounded border border-border bg-background px-1 font-mono text-[10px] text-muted md:inline">
          Ctrl K
        </kbd>
      </button>

      <LanguageSwitcher />
      <ThemeToggle />
      <NotificationBell />

      <div className="flex items-center gap-2 rounded-full border border-border bg-surface py-1 pr-3 pl-1">
        <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-brand text-xs font-semibold text-brand-foreground uppercase">
          {email.charAt(0) || '?'}
        </span>
        <div className="hidden min-w-0 leading-tight md:block">
          <p className="max-w-[12rem] truncate text-xs font-medium text-foreground">{email}</p>
          <p className="text-[10px] text-muted">{roleLabel}</p>
        </div>
      </div>
    </header>
  )
}
