// État d'erreur (SPEC §7) : message rassurant et action de réessai. Annoncé
// aux lecteurs d'écran (role="alert"). Le texte est fourni par l'appelant.
import { TriangleAlert } from 'lucide-react'
import { Button } from './Button.tsx'
import { cn } from '../../lib/utils.ts'

export interface ErrorStateProps {
  title: string
  description?: string
  retryLabel: string
  onRetry?: () => void
  className?: string
}

export function ErrorState({
  title,
  description,
  retryLabel,
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        'flex flex-col items-center justify-center gap-3 rounded-lg border border-danger/30 bg-danger/5 px-6 py-12 text-center',
        className,
      )}
    >
      <span className="rounded-full bg-surface p-3 text-danger">
        <TriangleAlert aria-hidden="true" className="size-6" />
      </span>
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">{title}</p>
        {description ? (
          <p className="mx-auto max-w-sm text-sm text-muted">{description}</p>
        ) : null}
      </div>
      {onRetry ? (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          {retryLabel}
        </Button>
      ) : null}
    </div>
  )
}
