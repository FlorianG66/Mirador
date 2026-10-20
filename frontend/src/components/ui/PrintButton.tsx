// Bouton d'export PDF (sous-phase 6c-i). L'export s'appuie sur l'impression du
// navigateur (« Enregistrer au format PDF ») : c'est la technique la plus simple
// retenue dans DECISIONS.md — aucune dépendance de génération côté serveur, rendu
// fidèle à l'écran et déjà utilisée pour la fiche légale. Le bouton lui-même
// disparaît à l'impression (classe `print:hidden`).
import { Printer } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from './Button.tsx'
import { cn } from '../../lib/utils.ts'

export interface PrintButtonProps {
  className?: string
}

export function PrintButton({ className }: PrintButtonProps) {
  const { t } = useTranslation()

  return (
    <Button
      type="button"
      variant="secondary"
      size="sm"
      className={cn('print:hidden', className)}
      onClick={() => window.print()}
    >
      <Printer aria-hidden="true" className="size-4" />
      {t('print.action')}
    </Button>
  )
}
