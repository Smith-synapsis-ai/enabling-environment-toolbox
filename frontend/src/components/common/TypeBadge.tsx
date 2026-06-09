import { TYPE_COLORS, typeBadgeNeedsDarkText } from '../../types';

interface TypeBadgeProps {
  type: string;
  className?: string;
}

export default function TypeBadge({ type, className = '' }: TypeBadgeProps) {
  const color = TYPE_COLORS[type] || '#546E7A';
  const textColor = typeBadgeNeedsDarkText(type) ? '#1A1A1A' : '#FFFFFF';

  return (
    <span
      className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold ${className}`}
      style={{ backgroundColor: color, color: textColor }}
    >
      {type}
    </span>
  );
}
