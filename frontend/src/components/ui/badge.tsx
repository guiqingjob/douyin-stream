import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-medium leading-[16px] uppercase tracking-[0.14em] border',
  {
    variants: {
      tone: {
        default:     'bg-transparent border-[var(--color-hairline-strong)] text-[var(--color-ash)]',
        secondary:   'bg-[rgba(198,107,62,0.08)] border-[var(--color-rust)]/40 text-[var(--color-rust)]',
        success:     'bg-[rgba(135,168,120,0.08)] border-[var(--color-patina)]/40 text-[var(--color-patina)]',
        warning:     'bg-[rgba(212,168,80,0.08)] border-[var(--color-ember)]/40 text-[var(--color-ember)]',
        destructive: 'bg-[rgba(178,89,80,0.08)] border-[var(--color-iron)]/40 text-[var(--color-iron)]',
        info:        'bg-[rgba(198,107,62,0.08)] border-[var(--color-rust)]/40 text-[var(--color-rust)]',
      },
      size: {
        default: 'px-2 py-0.5',
        sm: 'px-1.5 py-0',
        lg: 'px-2.5 py-1',
      },
    },
    defaultVariants: {
      tone: 'default',
      size: 'default',
    },
  }
)

export function Badge({
  className,
  tone,
  size,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone, size }), className)} {...props} />
}
