// Élément de navigation du menu latéral : NavLink avec état actif visible et
// accessibilité clavier. Le libellé est fourni par le parent (i18n).
import type { LucideIcon } from 'lucide-react'
import { NavLink } from 'react-router'
import { cn } from '../../lib/utils.ts'

export interface SidebarNavItemProps {
  to: string
  icon: LucideIcon
  label: string
  end?: boolean
  onNavigate?: () => void
}

export function SidebarNavItem({
  to,
  icon: Icon,
  label,
  end,
  onNavigate,
}: SidebarNavItemProps) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
          isActive
            ? 'bg-brand-muted text-brand'
            : 'text-muted hover:bg-surface-hover hover:text-foreground',
        )
      }
    >
      <Icon aria-hidden="true" className="size-5 shrink-0" />
      {label}
    </NavLink>
  )
}
