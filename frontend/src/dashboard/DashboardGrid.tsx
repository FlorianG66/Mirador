// Grille du tableau de bord (sous-phase 6b-ii-b) : enveloppe react-grid-layout
// pour rendre les widgets déplaçables et redimensionnables en mode édition. En
// lecture, la grille est immobile : elle se contente d'afficher la disposition
// enregistrée. La largeur du conteneur est mesurée localement (avec un repli sûr
// hors navigateur, utile aux tests) pour ne pas dépendre d'un ResizeObserver.
import { useEffect, useRef, useState, type ReactNode, type Ref } from 'react'
import { GridLayout, type Layout, type ResizeHandleAxis } from 'react-grid-layout'
import { GRID_COLUMNS, GRID_MARGIN, ROW_HEIGHT } from './layout.ts'

export interface DashboardGridProps {
  layout: Layout
  /** Vrai en mode personnalisation : autorise le déplacement et le redimensionnement. */
  editable: boolean
  onLayoutChange: (layout: Layout) => void
  children: ReactNode
}

export function DashboardGrid({
  layout,
  editable,
  onLayoutChange,
  children,
}: DashboardGridProps) {
  const { ref, width } = useContainerWidth()

  return (
    <div ref={ref} className="w-full">
      <GridLayout
        width={width}
        layout={layout}
        gridConfig={{
          cols: GRID_COLUMNS,
          rowHeight: ROW_HEIGHT,
          margin: GRID_MARGIN,
          containerPadding: [0, 0],
        }}
        dragConfig={{ enabled: editable, handle: '.widget-handle', allowMobileScroll: true }}
        resizeConfig={{
          enabled: editable,
          handles: ['se'],
          handleComponent: renderResizeHandle,
        }}
        onLayoutChange={onLayoutChange}
      >
        {children}
      </GridLayout>
    </div>
  )
}

/** Poignée de redimensionnement (coin bas-droit) affichée en mode édition. */
function renderResizeHandle(_axis: ResizeHandleAxis, ref: Ref<HTMLElement>) {
  return (
    <span
      ref={ref as Ref<HTMLSpanElement>}
      aria-hidden="true"
      className="absolute right-0 bottom-0 h-3 w-3 cursor-se-resize"
      style={{
        borderRight: '2px solid var(--border-strong)',
        borderBottom: '2px solid var(--border-strong)',
      }}
    />
  )
}

/**
 * Largeur mesurée du conteneur, avec repli sûr (hors navigateur, la largeur
 * mesurée vaut 0 : on garde la valeur par défaut). Sans ResizeObserver
 * (environnements de test), on se rabat sur l'écoute de `resize`.
 */
function useContainerWidth(fallback = 1200) {
  const ref = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(fallback)

  useEffect(() => {
    const element = ref.current
    if (!element) return
    const measure = () => {
      const measured = element.clientWidth
      if (measured > 0) setWidth(measured)
    }
    measure()
    if (typeof ResizeObserver === 'function') {
      const observer = new ResizeObserver(measure)
      observer.observe(element)
      return () => observer.disconnect()
    }
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [fallback])

  return { ref, width }
}
