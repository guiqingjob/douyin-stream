import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center gap-2 border border-transparent bg-clip-padding font-medium whitespace-nowrap transition-all duration-200 ease-out outline-none select-none disabled:pointer-events-none disabled:opacity-40 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        primary:
          "bg-primary text-primary-foreground hover:bg-primary/90 active:bg-primary/85",
        secondary:
          "border border-border/60 bg-secondary text-secondary-foreground hover:bg-secondary/80 aria-expanded:bg-secondary",
        outline:
          "border border-border/60 bg-background/80 text-foreground hover:bg-secondary/80 aria-expanded:bg-secondary",
        ghost:
          "bg-transparent text-primary hover:bg-primary/10 active:bg-primary/15",
        destructive:
          "bg-transparent text-destructive hover:bg-destructive/10 active:bg-destructive/15",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default:
          "h-10 px-5 text-[14px] rounded-[var(--radius-control)] has-data-[icon=inline-end]:pr-3.5 has-data-[icon=inline-start]:pl-3.5",
        sm: "h-9 px-3.5 text-[13px] rounded-[var(--radius-control)] has-data-[icon=inline-end]:pr-2.5 has-data-[icon=inline-start]:pl-2.5 [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-12 px-6 text-[15px] rounded-[var(--radius-control)] has-data-[icon=inline-end]:pr-4 has-data-[icon=inline-start]:pl-4 [&_svg:not([class*='size-'])]:size-5",
        "icon": "size-10 p-0 rounded-[var(--radius-control)]",
        "icon-sm": "size-9 p-0 rounded-[var(--radius-control)] [&_svg:not([class*='size-'])]:size-3.5",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "primary",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(
        "focus-visible:ring-2 focus-visible:ring-ring/50 active:scale-[0.97] spring-transition",
        buttonVariants({ variant, size, className })
      )}
      {...props}
    />
  )
}

export { Button }
