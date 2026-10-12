// Liste classée (sous-phase 5a) : un nom, un rang, un montant — pour les tops
// clients/fournisseurs. Le contenu vient de l'API (dimensions du point) via les
// props ; les libellés sont traduits par l'appelant.
export interface RankedItem {
  name: string
  amount: number
}

export interface RankedListProps {
  items: RankedItem[]
  /** Formate le montant selon la langue active (ex. devise). */
  formatAmount: (value: number) => string
  /** Intro accessible expliquant ce que la liste classe (ex. « Top clients »). */
  summary: string
}

export function RankedList({ items, formatAmount, summary }: RankedListProps) {
  const total = items.reduce((sum, item) => sum + item.amount, 0)

  return (
    <ol role="list" aria-label={summary} className="space-y-1">
      {items.map((item, index) => {
        const share = total > 0 ? (item.amount / total) * 100 : 0
        return (
          <li
            key={item.name}
            className="flex items-center gap-3 rounded-md px-2 py-1.5 transition-colors hover:bg-surface-muted"
          >
            <span
              aria-hidden="true"
              className="flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold tabular-nums text-muted"
            >
              {index + 1}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-2">
                <p className="truncate text-sm font-medium">{item.name}</p>
                <p className="shrink-0 text-sm font-semibold tabular-nums">
                  {formatAmount(item.amount)}
                </p>
              </div>
              <div className="mt-1 h-1 overflow-hidden rounded-full bg-surface-muted">
                <div
                  className="h-full rounded-full bg-brand/70"
                  style={{ width: `${Math.min(share, 100)}%` }}
                />
              </div>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
