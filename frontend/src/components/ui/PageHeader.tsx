// En-tête de page partagé : titre, sous-titre et actions optionnelles. Il donne
// le même rythme vertical à toutes les pages de la coquille. Quand `printable`
// est vrai (sous-phase 6c-i), il ajoute un bouton « Exporter en PDF » et un
// bandeau de document imprimable ; à l'impression, les actions (boutons)
// disparaissent, le titre reste et le bandeau (produit + date + période)
// apparaît.
import type { ReactNode } from 'react'
import { cn } from '../../lib/utils.ts'
import { PrintButton } from './PrintButton.tsx'
import { PrintHeader } from './PrintHeader.tsx'

export interface PageHeaderProps {
  title: string
  subtitle?: string
  actions?: ReactNode
  /** Ajoute l'export PDF (bouton + bandeau de document) pour cette page. */
  printable?: boolean
  /** Période à rappeler sur le document imprimé (libellé déjà traduit). */
  printPeriod?: string
  className?: string
}

export function PageHeader({
  title,
  subtitle,
  actions,
  printable = false,
  printPeriod,
  className,
}: PageHeaderProps) {
  const hasActions = actions !== undefined || printable

  return (
    <header className={cn('flex flex-wrap items-end justify-between gap-4', className)}>
      {printable ? <PrintHeader period={printPeriod} /> : null}
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {subtitle ? <p className="text-sm text-muted">{subtitle}</p> : null}
      </div>
      {hasActions ? (
        <div className="flex items-center gap-2 print:hidden">
          {actions}
          {printable ? <PrintButton /> : null}
        </div>
      ) : null}
    </header>
  )
}
