// Enveloppe de graphique : titre, actions, et gestion des états chargement /
// vide / prêt, pour homogénéiser tous les widgets de données (SPEC §7).
import type { ReactNode } from 'react'
import { BarChart3 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from './Card.tsx'
import { EmptyState } from './EmptyState.tsx'
import { Skeleton } from './Skeleton.tsx'
import { cn } from '../../lib/utils.ts'

export interface ChartCardProps {
  title: string
  description?: string
  actions?: ReactNode
  loading?: boolean
  empty?: boolean
  emptyTitle: string
  emptyDescription?: string
  children?: ReactNode
  className?: string
}

export function ChartCard({
  title,
  description,
  actions,
  loading = false,
  empty = false,
  emptyTitle,
  emptyDescription,
  children,
  className,
}: ChartCardProps) {
  return (
    <Card className={cn('flex flex-col', className)}>
      <CardHeader className="flex-row items-start justify-between gap-4">
        <div className="space-y-1">
          <CardTitle>{title}</CardTitle>
          {description ? (
            <p className="text-sm text-muted">{description}</p>
          ) : null}
        </div>
        {actions}
      </CardHeader>
      <CardContent className="flex-1">
        {loading ? (
          <Skeleton className="h-64 w-full" />
        ) : empty ? (
          <EmptyState
            icon={BarChart3}
            title={emptyTitle}
            description={emptyDescription}
          />
        ) : (
          <div className="h-64 w-full">{children}</div>
        )}
      </CardContent>
    </Card>
  )
}
