// État du rail de navigation (replié/déplié), mémorisé dans localStorage pour
// retrouver la même disposition au rechargement.
import { useEffect, useState } from 'react'

const STORAGE_KEY = 'mirador-rail-collapsed'

export function useRailCollapsed() {
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(STORAGE_KEY) === '1')

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0')
  }, [collapsed])

  const toggle = () => setCollapsed((current) => !current)

  return { collapsed, toggle }
}
