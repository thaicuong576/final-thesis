import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "border border-amber-border bg-amber text-ink font-semibold shadow-tactile hover:bg-amber-hover active:translate-y-[1px] active:shadow-none",
        destructive:
          "border border-[#a83226] bg-destructive text-destructive-foreground font-semibold shadow-[0_2px_0_rgba(120,20,15,0.45)] hover:bg-[#b03d32] active:translate-y-[1px] active:shadow-none",
        outline:
          "border border-border bg-card text-ink font-medium shadow-none hover:bg-surface-hover hover:border-border-strong active:bg-surface-selected",
        secondary:
          "border border-border bg-secondary text-ink font-medium shadow-none hover:bg-surface-hover active:bg-surface-selected",
        ghost: "hover:bg-surface-hover hover:text-ink font-medium",
        link: "text-amber-active underline-offset-4 hover:underline font-medium",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
        icon: "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
