import * as React from 'react'

import { cn } from '@/lib/utils'

export function PageShell({
  variant = 'default',
  className,
  children,
}: {
  variant?: 'default' | 'wide'
  className?: string
  children: React.ReactNode
}) {
  return (
    <div
      className={cn(
        'mx-auto w-full px-6 py-8',
        variant === 'wide'
          ? 'max-w-[1200px] xl:max-w-[1400px] 2xl:max-w-[1600px]'
          : 'max-w-[960px] xl:max-w-[1100px] 2xl:max-w-[1280px]',
        className
      )}
    >
      {children}
    </div>
  )
}

