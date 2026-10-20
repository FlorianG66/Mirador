// Bandeau de document affiché uniquement à l'impression (sous-phase 6c-i) : nom
// du produit, date de génération et, le cas échéant, période rappelée. Il ne
// répète pas le titre de la page — celui-ci reste l'en-tête imprimé — ce qui
// évite tout doublon de titre à l'écran comme dans l'arbre d'accessibilité.
// Aucun texte en dur (AGENTS.md §7).
import { useTranslation } from 'react-i18next'
import { PROJECT_NAME } from '../../constants.ts'

export interface PrintHeaderProps {
  /** Libellé de période déjà traduit (ex. « 30 j »), optionnel. */
  period?: string
}

export function PrintHeader({ period }: PrintHeaderProps) {
  const { t, i18n } = useTranslation()
  const generatedOn = new Intl.DateTimeFormat(i18n.language, {
    dateStyle: 'long',
    timeStyle: 'short',
  }).format(new Date())

  return (
    <p className="hidden w-full border-b border-border pb-2 text-xs text-muted print:block">
      {PROJECT_NAME} · {t('print.generatedOn', { date: generatedOn })}
      {period ? ` · ${t('print.period', { period })}` : ''}
    </p>
  )
}
