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

/** Entier localisé (compteurs de visites, sessions, pages vues…). */
export function formatInteger(value: number, language: string): string {
  return new Intl.NumberFormat(language, { maximumFractionDigits: 0 }).format(value)
}

/** Ratio (0→1) affiché en pourcentage localisé (ex. 0.042 → « 4,2 % »). */
export function formatPercent(ratio: number, language: string): string {
  return new Intl.NumberFormat(language, {
    style: 'percent',
    maximumFractionDigits: 1,
  }).format(ratio)
}

/** Durée en secondes, localisée (ex. « 3 min 12 s »), sans texte en dur. */
export function formatDuration(seconds: number, language: string): string {
  const minutes = Math.floor(seconds / 60)
  const rest = Math.round(seconds % 60)
  const minuteUnit = new Intl.NumberFormat(language, {
    style: 'unit',
    unit: 'minute',
    unitDisplay: 'short',
  }).format(minutes)
  const secondUnit = new Intl.NumberFormat(language, {
    style: 'unit',
    unit: 'second',
    unitDisplay: 'short',
  }).format(rest)
  return `${minuteUnit} ${secondUnit}`
}

/** Nom d'un pays (code ISO 3166-1 alpha-2) localisé via `Intl.DisplayNames`. */
export function formatCountry(code: string, language: string): string {
  return new Intl.DisplayNames([language], { type: 'region' }).of(code) ?? code
}

/** Durée en jours, localisée (ex. « 6 jours »), sans texte en dur. */
export function formatDays(days: number, language: string): string {
  return new Intl.NumberFormat(language, {
    style: 'unit',
    unit: 'day',
    unitDisplay: 'short',
  }).format(days)
}
