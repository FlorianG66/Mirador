// Formatage des valeurs du panneau financier (SPEC §3, §7). Tout passe par
// Intl.NumberFormat afin de respecter la langue active (fr/en) et les règles de
// la locale ; les composants n'initialisent jamais leur propre formatage.
import type { MetricPoint } from '../api/types'

/** Monnaie complète (tables, infobulles) : des espaces fines selon la locale. */
export function formatCurrency(value: number, language: string): string {
  return new Intl.NumberFormat(language, {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  }).format(value)
}

/** Monnaie compacte (KPI, axes de graphique) : ex. « 42,1 k € ». */
export function formatCurrencyShort(value: number, language: string): string {
  return new Intl.NumberFormat(language, {
    style: 'currency',
    currency: 'EUR',
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value)
}

/** Libellé court d'un jour ISO (axe X des graphiques), ex. « 31 août ». */
export function formatDay(isoDate: string, language: string): string {
  return new Intl.DateTimeFormat(language, { day: '2-digit', month: 'short' }).format(
    new Date(isoDate),
  )
}

/** Libellé long d'un jour ISO (infobulle des graphiques). */
export function formatDayLong(isoDate: string, language: string): string {
  return new Intl.DateTimeFormat(language, {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  }).format(new Date(isoDate))
}

/** Dernier point d'une série (donnée la plus récente du widget). */
export function lastPoint(points: MetricPoint[]): MetricPoint | undefined {
  return points.at(-1)
}

/**
 * Tendance en pourcentage entre le dernier point et le précédent (la valeur
 * affichée par KpiCard est un pourcentage, ex. 4.5 → « +4,5 % »).
 * Renvoie undefined s'il n'y a pas assez de points pour comparer.
 */
export function lastValueTrend(points: MetricPoint[]): number | undefined {
  const current = points.at(-1)
  const previous = points.at(-2)
  if (current === undefined || previous === undefined || previous.value === 0) {
    return undefined
  }
  return ((current.value - previous.value) / Math.abs(previous.value)) * 100
}
