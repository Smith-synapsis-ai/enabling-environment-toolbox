import { cn } from '@/lib/utils'
import { getPillarColor, getEnablerColor, getStageColor, PILLARS, ENABLERS, STAGES } from '@/lib/constants'

interface TagPillProps {
  label: string
  onClick?: () => void
  active?: boolean
  size?: 'sm' | 'xs'
  className?: string
}

function getTagStyle(label: string): { bg: string; text: string } {
  if ((PILLARS as readonly string[]).includes(label)) {
    return getPillarColor(label)
  }
  if ((ENABLERS as readonly string[]).includes(label)) {
    return getEnablerColor(label)
  }
  if ((STAGES as readonly string[]).includes(label)) {
    return getStageColor(label)
  }
  return { bg: '#F3F4F6', text: '#374151' }
}

export function TagPill({ label, onClick, active, size = 'sm', className }: TagPillProps) {
  const style = getTagStyle(label)

  return (
    <span
      onClick={onClick}
      className={cn(
        "inline-flex items-center rounded-full font-medium transition-all duration-150",
        size === 'sm' && "px-3 py-1 text-xs",
        size === 'xs' && "px-2 py-0.5 text-[10px]",
        onClick && "cursor-pointer hover:opacity-80 hover:shadow-sm",
        active && "ring-2 ring-offset-1",
        className
      )}
      style={{
        backgroundColor: active ? style.text : style.bg,
        color: active ? 'white' : style.text,
        ...(active && { ringColor: style.text }),
      }}
    >
      {label}
    </span>
  )
}
