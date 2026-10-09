// Classes de bouton partagées. Isolées du composant Button pour que le module
// qui exporte un composant n'exporte que des composants (règle react-refresh)
// et pour pouvoir styler un <Link> à l'identique.
import { cn } from '../../lib/utils.ts'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
export type ButtonSize = 'sm' | 'md'

const base =
  'inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 ' +
  'focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50'

const variants: Record<ButtonVariant, string> = {
  primary: 'bg-brand text-brand-foreground hover:opacity-90',
  secondary:
    'border border-border bg-surface text-foreground hover:bg-surface-hover',
  ghost: 'text-muted hover:bg-surface-hover hover:text-foreground',
  danger: 'bg-danger text-danger-foreground hover:opacity-90',
}

const sizes: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-sm',
  md: 'h-10 px-4 text-sm',
}

export interface ButtonVariantsOptions {
  variant?: ButtonVariant
  size?: ButtonSize
  className?: string
}

export function buttonVariants({
  variant = 'primary',
  size = 'md',
  className,
}: ButtonVariantsOptions = {}): string {
  return cn(base, variants[variant], sizes[size], className)
}
