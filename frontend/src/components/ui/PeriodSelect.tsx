// Sélecteur de période (sous-phase 6a-ii) : un « segmented control » sans état
// interne, calqué sur le sélecteur de langue. La page pilote la valeur et la
// traduit ; le composant se contente d'exposer des boutons accessibles
// (aria-pressed) et un intitulé de groupe pour les lecteurs d'écran.
import { cn } from '../../lib/utils.ts'

export interface PeriodOption {
  value: number
  /** Libellé déjà traduit (ex. « 30 j ») : le composant ne traduit rien. */
  label: string
}

export interface PeriodSelectProps {
  label: string
  options: readonly PeriodOption[]
  value: number
  onChange: (value: number) => void
  className?: string
}

export function PeriodSelect({ label, options, value, onChange, className }: PeriodSelectProps) {
  return (
    <div
      role="group"
      aria-label={label}
      className={cn('inline-flex rounded-md border border-border bg-surface p-0.5', className)}
    >
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-pressed={option.value === value}
          onClick={() => onChange(option.value)}
          className={cn(
            'rounded px-2 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
            option.value === value
              ? 'bg-brand text-brand-foreground'
              : 'text-muted hover:text-foreground',
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
