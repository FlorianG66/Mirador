// Sélecteur de langue FR/EN (segmented control). La langue active est marquée
// par aria-pressed ; i18next met à jour <html lang> via son écouteur.
import { useTranslation } from 'react-i18next'
import { cn } from '../../lib/utils.ts'

const LANGUAGES = [
  { code: 'fr', labelKey: 'common.languageFr' },
  { code: 'en', labelKey: 'common.languageEn' },
] as const

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation()
  const current = i18n.language.startsWith('en') ? 'en' : 'fr'

  return (
    <div
      role="group"
      aria-label={t('common.language')}
      className="inline-flex rounded-md border border-border bg-surface p-0.5"
    >
      {LANGUAGES.map((language) => (
        <button
          key={language.code}
          type="button"
          aria-pressed={current === language.code}
          onClick={() => {
            void i18n.changeLanguage(language.code)
          }}
          className={cn(
            'rounded px-2 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
            current === language.code
              ? 'bg-brand text-brand-foreground'
              : 'text-muted hover:text-foreground',
          )}
        >
          {t(language.labelKey)}
        </button>
      ))}
    </div>
  )
}
