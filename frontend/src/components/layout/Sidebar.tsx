// Menu latéral gauche (SPEC §7). Sur desktop il est statique dans la grille de
// l'AppShell ; sur mobile il glisse depuis la gauche et la fermeture est gérée
// par l'AppShell (clic sur l'overlay ou touche Échap).
import type { LucideIcon } from 'lucide-react'
import {
  BarChart3,
  Landmark,
  LayoutDashboard,
  ListChecks,
  Share2,
  Users,
  Wallet,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { ModuleKey } from '../../api/types.ts'
import { useAuth } from '../../auth/context.ts'
import { PROJECT_NAME } from '../../constants.ts'
import { cn } from '../../lib/utils.ts'
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
}

// Un module est visible si l'utilisateur a au moins la lecture ; un admin voit
// tout. La page � �quipe � n'appara�t que pour les admins.
function canSee(moduleKey: ModuleKey | undefined, permissions: ReturnType<typeof useAuth>['permissions']): boolean {
  if (!permissions) {
    return false
  }
  if (permissions.role === 'admin') {
    return true
  }
  if (moduleKey === undefined) {
    return false
  }
  return (permissions.modules[moduleKey] ?? 'none') !== 'none'
}

export function Sidebar({ open, onNavigate }: SidebarProps) {
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
    ...allModules.filter((entry) => canSee(entry.moduleKey, permissions)),
  ]

  const settings: NavEntry[] =
    permissions?.role === 'admin' ? [{ to: '/team', icon: Users, label: t('nav.team') }] : []

  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-border bg-surface transition-transform duration-200 lg:static lg:translate-x-0',
        open ? 'translate-x-0' : '-translate-x-full',
      )}
    >
      <div className="flex h-16 items-center gap-2 border-b border-border px-5">
        <span className="flex size-8 items-center justify-center rounded-md bg-brand text-sm font-semibold text-brand-foreground">
          {PROJECT_NAME.charAt(0).toUpperCase()}
        </span>
        <span className="font-semibold">{PROJECT_NAME}</span>
      </div>

      <nav
        aria-label={t('nav.primaryAria')}
        className="flex-1 space-y-6 overflow-y-auto p-3"
      >
        <NavGroup
          label={t('nav.moduleLabel')}
          entries={modules}
          onNavigate={onNavigate}
        />
        <NavGroup
          label={t('nav.settingsLabel')}
          entries={settings}
          onNavigate={onNavigate}
        />
      </nav>
    </aside>
  )
}

function NavGroup({
  label,
  entries,
  onNavigate,
}: {
  label: string
  entries: NavEntry[]
  onNavigate?: () => void
}) {
  return (
    <div>
      <p className="px-3 pb-2 text-xs font-semibold tracking-wider text-muted uppercase">
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
          />
        ))}
      </div>
    </div>
  )
}
