// Badge de provenance d'un champ de la fiche légale (sous-phase 5e-c) : indique
// si la valeur vient du registre, d'une saisie manuelle ou d'un calcul, et à
// quelle date elle a été synchronisée (SPEC §3 « source et date de chaque
// donnée »). Le libellé et la date viennent de l'i18n / d'`Intl`.
import { useTranslation } from 'react-i18next'
import { formatDateTime } from './mentions.ts'

export interface ProvenanceBadgeProps {
  /** Source renvoyée par l'API : `registry`, `manual`, `computed`… */
  source: string | undefined
  /** Date de synchronisation ISO 8601 (facultative). */
  syncedAt: string | null | undefined
}

export function ProvenanceBadge({ source, syncedAt }: ProvenanceBadgeProps) {
  const { t, i18n } = useTranslation()
  if (!source) {
    return null
  }

  const label = t(`legal.provenance.${source}`, { defaultValue: source })
  const date = formatDateTime(syncedAt, i18n.language)

  return (
    <span
      className="inline-flex items-center gap-1 rounded-full border border-border bg-surface-muted px-2 py-0.5 text-xs text-muted"
      title={date ? t('legal.syncedAt', { date }) : undefined}
    >
      {label}
      {date ? <span>· {date}</span> : null}
    </span>
  )
}
