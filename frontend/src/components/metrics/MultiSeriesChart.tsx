// Graphique multi-séries réutilisable (sous-phase 5a, SPEC §7) : une même
// enveloppe Recharts rend area / bar / line, avec libellés fournis par l'i18n
// (jamais encodés ici) et couleurs issues des tokens de thème (variables CSS →
// clair/sombre automatiques).
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

export type ChartVariant = 'area' | 'bar' | 'line'

export interface SeriesDef {
  /** Nom du champ de données (dataKey de Recharts). */
  key: string
  /** Nom affiché dans la légende et l'infobulle (déjà traduit). */
  name: string
  /** Couleur au format valide SVG (variable CSS du thème de préférence). */
  color: string
}

/** Un point de graphique : un libellé d'axe X et une valeur par série. */
export interface ChartDatum {
  label: string
  [key: string]: string | number
}

export interface MultiSeriesChartProps {
  data: ChartDatum[]
  series: SeriesDef[]
  variant?: ChartVariant
  /** Formate les valeurs des infobulles (ex. devises). */
  formatValue?: (value: number) => string
  /** Formate les graduations de l'axe Y (ex. devises compactes). */
  formatAxis?: (value: number) => string
  /** Formate les graduations de l'axe X (les données portent une date ISO). */
  formatAxisLabel?: (label: string) => string
  /** Formate le libellé de l'infobulle (ex. date longue). */
  labelFormatter?: (label: string) => string
  /** Description courte passée à la lectrice ; le graphique reste décoratif. */
  ariaLabel?: string
  className?: string
}

export function MultiSeriesChart({
  data,
  series,
  variant = 'area',
  formatValue,
  formatAxis,
  formatAxisLabel,
  labelFormatter,
  ariaLabel,
  className,
}: MultiSeriesChartProps) {
  const chart = (children: React.ReactNode) =>
    variant === 'bar' ? (
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        {children}
      </BarChart>
    ) : variant === 'line' ? (
      <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        {children}
      </LineChart>
    ) : (
      <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        {children}
      </AreaChart>
    )

  const marks = series.map((def) =>
    variant === 'bar' ? (
      <Bar
        key={def.key}
        dataKey={def.key}
        name={def.name}
        fill={def.color}
        radius={[4, 4, 0, 0]}
        maxBarSize={22}
      />
    ) : variant === 'line' ? (
      <Line
        key={def.key}
        type="monotone"
        dataKey={def.key}
        name={def.name}
        stroke={def.color}
        strokeWidth={2}
        dot={false}
        activeDot={{ r: 3 }}
      />
    ) : (
      <Area
        key={def.key}
        type="monotone"
        dataKey={def.key}
        name={def.name}
        stroke={def.color}
        strokeWidth={2}
        fill={def.color}
        fillOpacity={0.12}
        activeDot={{ r: 3 }}
      />
    ),
  )

  return (
    <div
      role="img"
      aria-label={ariaLabel}
      className={className}
      style={{ width: '100%', height: '100%' }}
    >
      <ResponsiveContainer width="100%" height="100%">
        {chart(
          <>
            <CartesianGrid
              stroke="var(--border)"
              strokeDasharray="3 3"
              vertical={false}
            />
            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={false}
              tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
              minTickGap={32}
              tickFormatter={formatAxisLabel}
            />
            <YAxis
              width={56}
              tickLine={false}
              axisLine={false}
              tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
              tickFormatter={formatAxis ?? ((value: number) => String(value))}
            />
            <Tooltip
              contentStyle={{
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border)',
                background: 'var(--surface)',
                color: 'var(--text)',
                fontSize: 12,
              }}
              labelStyle={{ fontWeight: 600 }}
              formatter={(value) => (formatValue ? formatValue(Number(value)) : String(value))}
              labelFormatter={(label) => (labelFormatter ? labelFormatter(String(label)) : undefined)}
              cursor={{ stroke: 'var(--border-strong)' }}
            />
            {marks}
            {series.length > 1 ? <Legend /> : null}
          </>,
        )}
      </ResponsiveContainer>
    </div>
  )
}
