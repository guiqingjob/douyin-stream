import * as React from "react"
import { Input as InputPrimitive } from "@base-ui/react/input"

import { cn } from "@/lib/utils"

function Input({
  className,
  type,
  icon,
  rightElement,
  ...props
}: React.ComponentProps<"input"> & {
  icon?: React.ReactNode
  rightElement?: React.ReactNode
}) {
  if (icon || rightElement) {
    return (
      <div className={cn("relative flex items-center gap-2 flex-1", !icon && !rightElement && className)}>
        {icon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
            {icon}
          </div>
        )}
        <InputPrimitive
          type={type}
          data-slot="input"
          className={cn(
            "h-10 w-full rounded-[var(--radius-control)] border border-border/60 bg-background px-3.5 text-[14px] text-foreground",
            "transition-all duration-200 ease-out outline-none",
            "placeholder:text-muted-foreground/60",
            "hover:border-border/80",
            "focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-ring/30",
            "disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-secondary/50 disabled:opacity-50",
            icon && "pl-9",
            rightElement && "pr-20",
            className
          )}
          {...props}
        />
        {rightElement && (
          <div className="absolute right-1 top-1/2 -translate-y-1/2">
            {rightElement}
          </div>
        )}
      </div>
    )
  }

  return (
    <InputPrimitive
      type={type}
      data-slot="input"
      className={cn(
        "h-10 w-full min-w-0 rounded-[var(--radius-control)] border border-border/60 bg-background px-3.5 text-[14px] text-foreground",
        "transition-all duration-200 ease-out outline-none",
        "file:inline-flex file:h-8 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground",
        "placeholder:text-muted-foreground/60",
        "hover:border-border/80",
        "focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-ring/30",
        "disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-secondary/50 disabled:opacity-50",
        "aria-invalid:border-destructive/50 aria-invalid:ring-2 aria-invalid:ring-destructive/20",
        className
      )}
      {...props}
    />
  )
}

export { Input }
