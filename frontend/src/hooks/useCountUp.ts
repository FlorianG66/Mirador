// Compteur animé : fait défiler une valeur vers sa cible (easing cubique),
// sans aucune temporisation si l'utilisateur demande de réduire les animations.
import { useEffect, useState } from 'react'
import { usePrefersReducedMotion } from './usePrefersReducedMotion.ts'

export function useCountUp(target: number, duration = 800): number {
  const prefersReducedMotion = usePrefersReducedMotion()
  const [value, setValue] = useState(prefersReducedMotion ? target : 0)

  useEffect(() => {
    if (prefersReducedMotion) {
      setValue(target)
      return
    }

    let frame = 0
    const start = performance.now()

    const tick = (now: number) => {
      const progress = Math.min((now - start) / duration, 1)
      const eased = 1 - (1 - progress) ** 3
      setValue(target * eased)
      if (progress < 1) frame = requestAnimationFrame(tick)
    }

    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [duration, prefersReducedMotion, target])

  return value
}
