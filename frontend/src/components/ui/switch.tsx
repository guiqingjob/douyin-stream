import * as React from "react"
import { Switch as SwitchPrimitive } from "@base-ui/react/switch"

import { cn } from "@/lib/utils"

function Switch({
  className,
  ...props
}: React.ComponentProps<typeof SwitchPrimitive>) {
  return (
    <SwitchPrimitive
      data-slot="switch"
      className={cn(
        "peer relative inline-flex h-[22px] w-[36px] shrink-0 cursor-pointer rounded-full border-0 bg-secondary transition-colors duration-200",
        "after:absolute after:left-[2px] after:top-[2px] after:h-[18px] after:w-[18px] after:rounded-full",
        "after:bg-white after:shadow-sm",
        "after:transition-all after:duration-200 after:spring-ease",
        "data-[state=checked]:bg-primary",
        "data-[state=checked]:after:left-[16px]",
        "data-[state=checked]:after:shadow-md",
        "data-[state=checked]:after:shadow-[0_1px_3px_rgba(0,122,255,0.3)]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
        "hover:data-[state=unchecked]:bg-secondary/80",
        "active:scale-[0.97]",
        className
      )}
      {...props}
    />
  )
}

export { Switch }
