import { Link } from 'react-router-dom'
import { MapPin, Calendar, Building2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { TypeBadge } from './TypeBadge'
import { TagPill } from './TagPill'
import type { Item, Tool, Story } from '@/data/items'

interface ItemCardProps {
  item: Item
  onTagClick?: (tag: string) => void
  className?: string
}

export function ItemCard({ item, onTagClick, className }: ItemCardProps) {
  if (item.kind === 'tool') {
    return <ToolCard tool={item} onTagClick={onTagClick} className={className} />
  }
  return <StoryCard story={item} onTagClick={onTagClick} className={className} />
}

function ToolCard({ tool, onTagClick, className }: { tool: Tool; onTagClick?: (tag: string) => void; className?: string }) {
  const allTags = [...tool.pillars, ...tool.enablers, tool.stage]

  return (
    <Link
      to={`/tool/${tool.id}`}
      className={cn(
        "group block bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden",
        className
      )}
    >
      <div className="p-5 flex flex-col h-full min-h-[240px]">
        <div className="flex items-center justify-between mb-3">
          <TypeBadge type={tool.type} />
          <span className="text-[10px] text-gray-400 font-medium">{tool.year}</span>
        </div>
        <h3 className="text-base font-bold text-[#1A1A2E] mb-2 group-hover:text-[#00524D] transition-colors leading-snug">
          {tool.title}
        </h3>
        <p className="text-sm text-[#4A5568] leading-relaxed line-clamp-3 flex-1 mb-3">
          {tool.description}
        </p>
        <div className="flex items-center gap-2 text-[10px] text-gray-400 mb-3">
          <Building2 size={10} />
          <span>{tool.source}</span>
        </div>
        <div className="flex flex-wrap gap-1.5 mt-auto">
          {allTags.slice(0, 3).map(tag => (
            <TagPill
              key={tag}
              label={tag}
              size="xs"
              onClick={onTagClick ? ((e?: React.MouseEvent) => { e?.preventDefault(); onTagClick(tag) }) as () => void : undefined}
            />
          ))}
          {allTags.length > 3 && (
            <span className="inline-flex items-center px-2 py-0.5 text-[10px] text-gray-400 font-medium">
              +{allTags.length - 3}
            </span>
          )}
        </div>
      </div>
    </Link>
  )
}

function StoryCard({ story, onTagClick, className }: { story: Story; onTagClick?: (tag: string) => void; className?: string }) {
  const allTags = [...story.pillars, ...story.enablers]

  return (
    <Link
      to={`/story/${story.id}`}
      className={cn(
        "group block bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden",
        className
      )}
    >
      <div className="relative h-40 overflow-hidden">
        <img
          src={story.image}
          alt={story.title}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent" />
        <div className="absolute bottom-3 left-3 flex items-center gap-2">
          <span className="inline-flex items-center gap-1 text-white text-xs font-medium">
            <MapPin size={11} />
            {story.region}
          </span>
          <span className="inline-flex items-center gap-1 text-white/70 text-[10px]">
            <Calendar size={9} />
            {story.year}
          </span>
        </div>
        <div className="absolute top-3 left-3">
          <span className="inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-bold tracking-widest uppercase bg-white/20 text-white backdrop-blur-sm border border-white/30">
            STORY
          </span>
        </div>
      </div>
      <div className="p-5">
        <h3 className="text-base font-bold text-[#1A1A2E] mb-2 group-hover:text-[#00524D] transition-colors leading-snug">
          {story.title}
        </h3>
        <p className="text-sm text-[#4A5568] leading-relaxed line-clamp-2 mb-3">
          {story.description}
        </p>
        <div className="flex items-center gap-2 text-[10px] text-gray-400 mb-3">
          <Building2 size={10} />
          <span>{story.source}</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {allTags.slice(0, 3).map(tag => (
            <TagPill
              key={tag}
              label={tag}
              size="xs"
              onClick={onTagClick ? ((e?: React.MouseEvent) => { e?.preventDefault(); onTagClick(tag) }) as () => void : undefined}
            />
          ))}
        </div>
      </div>
    </Link>
  )
}
