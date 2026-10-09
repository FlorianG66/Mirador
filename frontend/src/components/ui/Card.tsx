// Carte et ses sous-parties : conteneur neutre en tokens, réutilisé partout
// (KPI, graphiques, états). On expose des primitives composables plutôt qu'une
// API monolithique.
import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '../../lib/utils.ts'

type DivProps = HTMLAttributes<HTMLDivElement>

export function Card({ className, ...rest }: DivProps) {
  return (
    <div
      className={cn(
        'rounded-lg border border-border bg-surface shadow-card',
        className,
      )}
      {...rest}
    />
  )
}

export function CardHeader({ className, ...rest }: DivProps) {
  return <div className={cn('flex flex-col gap-1 p-5', className)} {...rest} />
}

export function CardTitle({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLHeadingElement> & { children: ReactNode }) {
  return (
    <h3 className={cn('text-base font-semibold tracking-tight', className)} {...rest}>
      {children}
    </h3>
  )
}

export function CardDescription({ className, ...rest }: DivProps) {
  return <p className={cn('text-sm text-muted', className)} {...rest} />
}

export function CardContent({ className, ...rest }: DivProps) {
  return <div className={cn('p-5 pt-0', className)} {...rest} />
}

export function CardFooter({ className, ...rest }: DivProps) {
  return (
    <div
      className={cn('flex items-center gap-2 px-5 pb-5', className)}
      {...rest}
    />
  )
}
