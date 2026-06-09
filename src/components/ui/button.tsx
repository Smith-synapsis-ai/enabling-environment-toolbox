import * as React from "react"
import { cn } from "@/lib/utils"

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
        variant === 'primary' && "bg-[#00524D] text-white hover:bg-[#003D39] focus-visible:ring-[#00524D]",
        variant === 'secondary' && "bg-[#E0F5F0] text-[#00524D] hover:bg-[#c5ede5] focus-visible:ring-[#00524D]",
        variant === 'outline' && "border border-[#00524D] text-[#00524D] bg-transparent hover:bg-[#E0F5F0]",
        variant === 'ghost' && "text-[#4A5568] hover:bg-gray-100",
        size === 'sm' && "px-3 py-1.5 text-sm",
        size === 'md' && "px-4 py-2 text-sm",
        size === 'lg' && "px-6 py-3 text-base",
        className
      )}
      {...props}
    />
  )
)
Button.displayName = "Button"

export { Button }
