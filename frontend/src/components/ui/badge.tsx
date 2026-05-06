import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-[9999px] px-2.5 py-0.5 text-[11px] font-semibold leading-[16px] uppercase tracking-[0.01em]',
  {
    variants: {
      tone: {
        default: 'bg-secondary text-muted-foreground',
        secondary: 'bg-primary/12 text-primary',
        success: 'bg-success/12 text-success',
        warning: 'bg-warning/14 text-warning',
        destructive: 'bg-destructive/12 text-destructive',
        info: 'bg-primary/12 text-primary',
      },
      size: {
        default: 'px-2.5 py-0.5',
        sm: 'px-2 py-0.5',
        lg: 'px-3 py-1',
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
