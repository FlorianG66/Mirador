// Rail de navigation (SPEC §7). Sur desktop il est fixé à gauche et se replie en
// icônes seules ; sur mobile il glisse depuis la gauche et sa fermeture est
// gérée par l'AppShell (overlay ou touche Échap). La largeur est pilotée par la
// variable CSS --rail-w posée par l'AppShell.
import type { LucideIcon } from 'lucide-react'
import {
  BarChart3,
  Landmark,
  LayoutDashboard,
  ListChecks,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  Share2,
  Users,
  Wallet,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import type { ModuleKey } from '../../api/types.ts'
import { useAuth } from '../../auth/context.ts'
import { PROJECT_NAME } from '../../constants.ts'
import { cn } from '../../lib/utils.ts'
import { canSeeModule } from '../../lib/permissions.ts'
import { SidebarNavItem } from './SidebarNavItem.tsx'

interface NavEntry {
  to: string
  icon: LucideIcon
  label: string
  end?: boolean
  moduleKey?: ModuleKey
}

export interface SidebarProps {
  open: boolean
  onNavigate?: () => void
  collapsed?: boolean
  onToggleCollapsed?: () => void
}

export function Sidebar({
  open,
  onNavigate,
  collapsed = false,
  onToggleCollapsed,
}: SidebarProps) {
  const { t } = useTranslation()
  const { permissions } = useAuth()

  const allModules: NavEntry[] = [
    { to: '/finance', moduleKey: 'finance', icon: Wallet, label: t('nav.finance') },
    { to: '/web', moduleKey: 'web', icon: BarChart3, label: t('nav.web') },
    { to: '/social', moduleKey: 'social', icon: Share2, label: t('nav.social') },
    { to: '/projects', moduleKey: 'projects', icon: ListChecks, label: t('nav.projects') },
    { to: '/legal', moduleKey: 'legal', icon: Landmark, label: t('nav.legal') },
  ]

  const modules: NavEntry[] = [
    { to: '/', end: true, icon: LayoutDashboard, label: t('nav.dashboard') },
    ...allModules.filter((entry) => entry.moduleKey && canSeeModule(entry.moduleKey, permissions)),
  ]

  const settings: NavEntry[] = [
    { to: '/settings', icon: Settings, label: t('nav.settings') },
    ...(permissions?.role === 'admin' ? [{ to: '/team', icon: Users, label: t('nav.team') }] : []),
  ]

  const toggleLabel = collapsed ? t('nav.expand') : t('nav.collapse')

  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-border bg-surface transition-[transform,width] duration-200 lg:translate-x-0 lg:w-[var(--rail-w)] print:hidden',
        open ? 'translate-x-0' : '-translate-x-full',
      )}
    >
      <div className={cn('flex h-16 items-center border-b border-border px-3', !collapsed && 'lg:px-5')}>
        <Link
          to="/"
          onClick={onNavigate}
          className={cn(
            'flex items-center gap-2 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
            collapsed && 'lg:justify-center',
          )}
        >
          <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-brand text-sm font-semibold text-brand-foreground">
            {PROJECT_NAME.charAt(0).toUpperCase()}
          </span>
          <span className={cn('font-semibold tracking-tight', collapsed && 'lg:hidden')}>
            {PROJECT_NAME}
          </span>
        </Link>
      </div>

      <nav
        aria-label={t('nav.primaryAria')}
        className={cn('flex-1 space-y-6 overflow-y-auto p-3', collapsed && 'lg:px-2')}
      >
        <NavGroup
          label={t('nav.moduleLabel')}
          entries={modules}
          onNavigate={onNavigate}
          collapsed={collapsed}
        />
        <NavGroup
          label={t('nav.settingsLabel')}
          entries={settings}
          onNavigate={onNavigate}
          collapsed={collapsed}
        />
      </nav>

      <div className={cn('border-t border-border p-3', collapsed && 'lg:px-2')}>
        <button
          type="button"
          onClick={onToggleCollapsed}
          aria-label={toggleLabel}
          title={toggleLabel}
          className={cn(
            'hidden w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted transition-colors hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand lg:inline-flex',
            collapsed && 'lg:justify-center lg:px-0',
          )}
        >
          {collapsed ? (
            <PanelLeftOpen aria-hidden="true" className="size-5 shrink-0" />
          ) : (
            <PanelLeftClose aria-hidden="true" className="size-5 shrink-0" />
          )}
          <span className={cn('truncate', collapsed && 'lg:hidden')}>{toggleLabel}</span>
        </button>
      </div>
    </aside>
  )
}

function NavGroup({
  label,
  entries,
  onNavigate,
  collapsed,
}: {
  label: string
  entries: NavEntry[]
  onNavigate?: () => void
  collapsed: boolean
}) {
  return (
    <div>
      <p
        className={cn(
          'px-3 pb-2 text-xs font-semibold tracking-wider text-muted uppercase',
          collapsed && 'lg:hidden',
        )}
      >
        {label}
      </p>
      <div className="space-y-1">
        {entries.map((entry) => (
          <SidebarNavItem
            key={entry.to}
            to={entry.to}
            icon={entry.icon}
            label={entry.label}
            end={entry.end}
            onNavigate={onNavigate}
            collapsed={collapsed}
          />
        ))}
      </div>
    </div>
  )
}
