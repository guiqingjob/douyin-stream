import * as React from 'react'

import { cn } from '@/lib/utils'

export type SegmentedTabItem = {
  value: string
  label: string
  icon?: React.ReactNode
  disabled?: boolean
}

export function SegmentedTabs({
  value,
  onValueChange,
  items,
  className,
}: {
  value: string
  onValueChange: (value: string) => void
  items: SegmentedTabItem[]
  className?: string
}) {
  return (
    <div
      role="tablist"
      className={cn(
        'inline-flex items-center rounded-full bg-muted p-1',
        className
      )}
    >
      {items.map((item) => {
        const isActive = item.value === value
        return (
          <button
            key={item.value}
            type="button"
            role="tab"
            aria-selected={isActive}
            disabled={item.disabled}
            onClick={() => {
              if (item.disabled) return
              onValueChange(item.value)
            }}
            className={cn(
              'inline-flex h-8 items-center justify-center gap-1.5 rounded-full px-3 text-[13px] font-medium outline-none transition-all duration-200',
              'focus-visible:ring-2 focus-visible:ring-ring/40',
              'disabled:pointer-events-none disabled:opacity-40',
              isActive
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            {item.icon ? <span className="shrink-0">{item.icon}</span> : null}
            <span className="whitespace-nowrap">{item.label}</span>
          </button>
        )
      })}
    </div>
  )
}

