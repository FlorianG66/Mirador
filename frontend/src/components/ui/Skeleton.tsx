// Bloc de chargement (skeleton) : pulsation désactivée si l'utilisateur
// demande de réduire les animations (motion-reduce).
import { cn } from '../../lib/utils.ts'

export interface SkeletonProps {
  className?: string
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        'animate-pulse rounded-md bg-surface-muted motion-reduce:animate-none',
        className,
      )}
    />
  )
}
