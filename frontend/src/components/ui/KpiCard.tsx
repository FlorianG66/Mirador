// Carte KPI : libellé, valeur (compteur animé, SPEC §7) et tendance optionnelle.
// Aucune donnée n'est inventée ici : la carte affiche ce que la page lui passe.
import type { LucideIcon } from 'lucide-react'
import { TrendingDown, TrendingUp } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useCountUp } from '../../hooks/useCountUp.ts'
import { Card, CardContent } from './Card.tsx'
import { cn } from '../../lib/utils.ts'

export interface KpiCardProps {
  label: string
  value: number
  unit?: string
  trend?: number
  decimals?: number
  icon?: LucideIcon
  className?: string
}

function formatNumber(
  value: number,
  locale: string,
  decimals: number,
): string {
  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

export function KpiCard({
  label,
  value,
  unit,
  trend,
  decimals = 0,
  icon: Icon,
  className,
}: KpiCardProps) {
  const { i18n } = useTranslation()
  const animated = useCountUp(value)
  const isUp = (trend ?? 0) >= 0
  const TrendIcon = isUp ? TrendingUp : TrendingDown

  return (
    <Card className={className}>
      <CardContent className="flex items-start justify-between gap-4 p-5">
        <div className="space-y-1">
          <p className="text-sm text-muted">{label}</p>
          <p className="text-2xl font-semibold tabular-nums">
            {formatNumber(animated, i18n.language, decimals)}
            {unit ? (
              <span className="ml-1 text-base font-normal text-muted">
                {unit}
              </span>
            ) : null}
          </p>
          {trend === undefined ? null : (
            <p
              className={cn(
                'flex items-center gap-1 text-xs font-medium',
                isUp ? 'text-success' : 'text-danger',
              )}
            >
              <TrendIcon aria-hidden="true" className="size-3.5" />
              {new Intl.NumberFormat(i18n.language, {
                style: 'percent',
                maximumFractionDigits: 1,
                signDisplay: 'exceptZero',
              }).format(trend / 100)}
            </p>
          )}
        </div>
        {Icon ? (
          <span className="rounded-md bg-brand-muted p-2 text-brand">
            <Icon aria-hidden="true" className="size-5" />
          </span>
        ) : null}
      </CardContent>
    </Card>
  )
}
