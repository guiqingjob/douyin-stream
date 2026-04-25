import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium leading-5',
  {
    variants: {
      tone: {
        default: 'bg-muted text-muted-foreground',
        secondary: 'bg-primary/10 text-primary',
        success: 'bg-success/12 text-success',
        warning: 'bg-warning/14 text-warning',
        destructive: 'bg-destructive/12 text-destructive',
      },
    },
    defaultVariants: {
      tone: 'default',
    },
  }
)

export function Badge({
  className,
  tone,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />
}
