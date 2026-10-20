// Palette de recherche globale (sous-phase 6b-i, SPEC §4) : dialogue ouvert par
// Ctrl/Cmd+K ou par le bouton de la barre supérieure, qui filtre l'index des
// pages et des KPI (items.ts) et navigue vers la route choisie (flèches +
// Entrée, ou clic). Le focus est géré à l'ouverture et rendu à la fermeture
// (WCAG AA) ; aucun texte en dur : tout passe par l'i18n (AGENTS.md §7).
import { useEffect, useMemo, useRef, useState } from 'react'
import { Search } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
import type { MyPermissionsOut } from '../api/types.ts'
import { cn } from '../lib/utils.ts'
import { buildSearchItems, searchItems, type SearchItem } from './items.ts'

export interface SearchPaletteProps {
  open: boolean
  onOpen: () => void
  onClose: () => void
  permissions: MyPermissionsOut | null
}

export function SearchPalette({ open, onOpen, onClose, permissions }: SearchPaletteProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const previousFocus = useRef<HTMLElement | null>(null)

  // L'index est reconstruit quand les permissions ou la langue changent ; le
  // filtrage, lui, dépend uniquement de la requête (liste courte, calcul direct).
  const items = useMemo(
    () => buildSearchItems(permissions, (key) => t(key)),
    [permissions, t],
  )
  const results = searchItems(query, items)
  const active = Math.min(activeIndex, results.length - 1)

  // Raccourci global : Ctrl/Cmd+K bascule la palette, Échap la ferme.
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() === 'k' && (event.ctrlKey || event.metaKey)) {
        event.preventDefault()
        if (open) onClose()
        else onOpen()
        return
      }
      if (open && event.key === 'Escape') {
        event.preventDefault()
        onClose()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onOpen, onClose])

  // À l'ouverture : mémorise l'élément focalisé et déplace le focus sur la
  // recherche. À la fermeture : remise à zéro et retour du focus à l'appelant.
  useEffect(() => {
    if (open) {
      previousFocus.current = (document.activeElement as HTMLElement | null) ?? null
      inputRef.current?.focus()
      return
    }
    setQuery('')
    setActiveIndex(0)
    previousFocus.current?.focus()
  }, [open])

  // La sélection revient au premier résultat dès que la requête change.
  useEffect(() => {
    setActiveIndex(0)
  }, [query])

  const go = (item: SearchItem) => {
    navigate(item.to)
    onClose()
  }

  const onInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActiveIndex((index) => Math.min(index + 1, results.length - 1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex((index) => Math.max(index - 1, 0))
    } else if (event.key === 'Enter' && results[active]) {
      event.preventDefault()
      go(results[active])
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-[10vh]">
      <div aria-hidden="true" onClick={onClose} className="fixed inset-0 bg-black/40" />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={t('search.title')}
        className="relative z-10 w-full max-w-lg overflow-hidden rounded-xl border border-border bg-surface shadow-raised"
      >
        <div className="flex items-center gap-3 border-b border-border px-4">
          <Search aria-hidden="true" className="size-4 shrink-0 text-muted" />
          <input
            ref={inputRef}
            type="search"
            role="combobox"
            aria-label={t('search.placeholder')}
            aria-expanded="true"
            aria-controls="search-results"
            aria-activedescendant={
              results[active] ? `search-option-${results[active].id}` : undefined
            }
            placeholder={t('search.placeholder')}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={onInputKeyDown}
            className="h-12 w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted"
          />
        </div>
        <ul
          id="search-results"
          role="listbox"
          aria-label={t('search.title')}
          className="max-h-80 overflow-y-auto p-1"
        >
          {results.length === 0 ? (
            <li role="presentation" className="px-3 py-6 text-center text-sm text-muted">
              {t('search.empty')}
            </li>
          ) : (
            results.map((item, index) => (
              <li
                key={item.id}
                id={`search-option-${item.id}`}
                role="option"
                aria-selected={index === active}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => go(item)}
                className={cn(
                  'flex cursor-pointer flex-col gap-0.5 rounded-md px-3 py-2 text-sm',
                  index === active ? 'bg-brand text-brand-foreground' : 'text-foreground',
                )}
              >
                <span className="font-medium">{item.label}</span>
                {item.hint ? (
                  <span
                    className={cn(
                      'text-xs',
                      index === active ? 'text-brand-foreground/70' : 'text-muted',
                    )}
                  >
                    {item.hint}
                  </span>
                ) : null}
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  )
}
