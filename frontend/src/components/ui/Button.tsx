// Bouton de base du design system : variantes sémantiques et tailles, tout en
// tokens. Aucun style métier ici — les pages composent ces primitives.
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import {
  buttonVariants,
  type ButtonSize,
  type ButtonVariant,
} from './button-variants.ts'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  children: ReactNode
}

export function Button({
  variant = 'primary',
  size = 'md',
  className,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={buttonVariants({ variant, size, className })}
      {...rest}
    >
      {children}
    </button>
  )
}
