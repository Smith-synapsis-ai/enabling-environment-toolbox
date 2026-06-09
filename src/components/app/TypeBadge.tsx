import { cn } from '@/lib/utils'
import { getTypeColor, getTypeBg } from '@/lib/constants'

interface TypeBadgeProps {
  type: string
  className?: string
}

export function TypeBadge({ type, className }: TypeBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-bold tracking-widest uppercase",
        className
      )}
      style={{
        backgroundColor: getTypeBg(type),
        color: getTypeColor(type),
      }}
    >
      {type}
    </span>
  )
}
