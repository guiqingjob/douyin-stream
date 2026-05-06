import * as React from "react"
import { Input as InputPrimitive } from "@base-ui/react/input"
import { X } from "lucide-react"

import { cn } from "@/lib/utils"

function Input({
  className,
  type,
  icon,
  rightElement,
  showClear = false,
  value,
  onChange,
  ...props
}: React.ComponentProps<"input"> & {
  icon?: React.ReactNode
  rightElement?: React.ReactNode
  showClear?: boolean
}) {
  const [focused, setFocused] = React.useState(false)
  
  const handleClear = () => {
    if (onChange && value !== undefined) {
      onChange({ target: { value: "" } } as React.ChangeEvent<HTMLInputElement>)
    }
  }

  const hasValue = value !== undefined && value !== null && String(value).length > 0
  const showClearButton = showClear && hasValue && focused

  const inputClassName = cn(
    "h-11 w-full min-w-0 rounded-[10px] border bg-background px-4 text-body text-foreground",
    "transition-all duration-200 spring-ease-subtle outline-none",
    "file:inline-flex file:h-8 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground",
    "placeholder:text-muted-foreground/60",
    "disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-secondary/50 disabled:opacity-50",
    "aria-invalid:border-destructive/50 aria-invalid:ring-2 aria-invalid:ring-destructive/20",
    focused 
      ? "border-primary shadow-[0_0_0_1px_rgba(0,122,255,0.15),0_0_20px_rgba(0,122,255,0.08)]" 
      : "border-border/60 hover:border-border/80",
    icon && "pl-11",
    (rightElement || showClearButton) && "pr-10",
    className
  )

  return (
    <div className="relative flex items-center flex-1">
      {icon && (
        <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none">
          {icon}
        </div>
      )}
      <InputPrimitive
        type={type}
        data-slot="input"
        value={value}
        onChange={onChange}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        className={inputClassName}
        {...props}
      />
      {showClearButton && !rightElement && (
        <button
          type="button"
          onClick={handleClear}
          className="absolute right-2 top-1/2 -translate-y-1/2 size-7 flex items-center justify-center rounded-full text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
        >
          <X size={16} />
        </button>
      )}
      {rightElement && !showClearButton && (
        <div className="absolute right-2 top-1/2 -translate-y-1/2">
          {rightElement}
        </div>
      )}
    </div>
  )
}

export { Input }
