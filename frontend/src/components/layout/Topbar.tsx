// Barre supérieure : bouton d'ouverture du menu en mobile, puis langue et
// thème. Reste discrète et collée en haut (sticky).
import { Menu } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { LanguageSwitcher } from './LanguageSwitcher.tsx'
import { ThemeToggle } from './ThemeToggle.tsx'

export interface TopbarProps {
  onOpenSidebar: () => void
}

export function Topbar({ onOpenSidebar }: TopbarProps) {
  const { t } = useTranslation()

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-border bg-background/80 px-4 backdrop-blur lg:px-6">
      <button
        type="button"
        onClick={onOpenSidebar}
        aria-label={t('common.openMenu')}
        className="inline-flex size-9 items-center justify-center rounded-md text-muted transition-colors hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand lg:hidden"
      >
        <Menu aria-hidden="true" className="size-5" />
      </button>
      <div className="flex-1" />
      <LanguageSwitcher />
      <ThemeToggle />
    </header>
  )
}
