import TypeBadge from '../common/TypeBadge';
import { Star } from 'lucide-react';
import type { ToolSearchResult } from '../../types';
import { TYPE_COLORS } from '../../types';

interface CatalogResultsProps {
  results: ToolSearchResult[];
  onToolClick: (tool: ToolSearchResult) => void;
}

export default function CatalogResults({ results, onToolClick }: CatalogResultsProps) {
  if (results.length === 0) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500 text-lg">No tools match your current filters.</p>
        <p className="text-gray-500 text-sm mt-1">Try adjusting or clearing your filters.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
      {results.map(tool => {
        const bgColor = TYPE_COLORS[tool.type] || '#607D8B';

        return (
          <button
            key={tool.id}
            onClick={() => onToolClick(tool)}
            className="bg-white rounded-xl shadow-sm hover:shadow-md border border-gray-100 overflow-hidden text-left transition-all group cursor-pointer"
          >
            {/* Cover */}
            {tool.cover_image_url ? (
              <img
                src={tool.cover_image_url}
                alt={tool.title}
                className="w-full h-40 object-cover"
              />
            ) : (
              <div
                className="w-full h-40 flex items-center justify-center"
                style={{ backgroundColor: bgColor + '12' }}
              >
                <div
                  className="w-14 h-14 rounded-full flex items-center justify-center text-white text-lg font-bold"
                  style={{ backgroundColor: bgColor }}
                >
                  {tool.title.charAt(0)}
                </div>
              </div>
            )}

            {/* Content */}
            <div className="p-4">
              <TypeBadge type={tool.type} className="mb-2" />
              <h3 className="text-sm font-semibold text-gray-900 line-clamp-2 mb-2 group-hover:text-cgiar-accent transition-colors">
                {tool.title}
              </h3>
              <p className="text-xs text-gray-500 line-clamp-3 mb-3">
                {tool.summary}
              </p>

              {/* Pillar tags */}
              {tool.pillars.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-3">
                  {tool.pillars.slice(0, 2).map(p => (
                    <span key={p} className="px-2 py-0.5 bg-cgiar-accent/10 text-cgiar-green text-xs rounded-full">
                      {p}
                    </span>
                  ))}
                  {tool.pillars.length > 2 && (
                    <span className="text-xs text-gray-500">+{tool.pillars.length - 2}</span>
                  )}
                </div>
              )}

              {/* Rating */}
              <div className="flex items-center gap-1" aria-label={`Rating: ${tool.average_rating.toFixed(1)} out of 5`} role="img">
                {[1, 2, 3, 4, 5].map(star => (
                  <Star
                    key={star}
                    size={12}
                    className={
                      star <= Math.round(tool.average_rating)
                        ? 'fill-yellow-400 text-yellow-400'
                        : 'fill-none text-gray-200'
                    }
                  />
                ))}
                {tool.rating_count > 0 && (
                  <span className="text-xs text-gray-500 ml-1">({tool.rating_count})</span>
                )}
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
