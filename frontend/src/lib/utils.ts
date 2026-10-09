// Utilitaires partagés du frontend.
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** Fusionne les classes Tailwind (clsx + tailwind-merge, la dernière gagne). */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}
