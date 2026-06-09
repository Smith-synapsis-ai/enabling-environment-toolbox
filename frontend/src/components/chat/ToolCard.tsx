import TypeBadge from '../common/TypeBadge';
import type { ToolSearchResult } from '../../types';
import { TYPE_COLORS } from '../../types';

interface ToolCardProps {
  tool: ToolSearchResult;
  onClick: () => void;
}

export default function ToolCard({ tool, onClick }: ToolCardProps) {
  const bgColor = TYPE_COLORS[tool.type] || '#607D8B';

  return (
    <button
      onClick={onClick}
      className="flex-shrink-0 w-64 bg-white rounded-xl shadow-lg overflow-hidden text-left hover:shadow-xl transition-shadow group cursor-pointer"
    >
      {/* Cover image or colored placeholder */}
      {tool.cover_image_url ? (
        <img
          src={tool.cover_image_url}
          alt={tool.title}
          className="w-full h-36 object-cover"
        />
      ) : (
        <div
          className="w-full h-36 flex items-center justify-center"
          style={{ backgroundColor: bgColor + '20' }}
        >
          <div
            className="w-16 h-16 rounded-full flex items-center justify-center text-white text-xl font-bold"
            style={{ backgroundColor: bgColor }}
          >
            {tool.title.charAt(0)}
          </div>
        </div>
      )}

      {/* Content */}
      <div className="p-4">
        <TypeBadge type={tool.type} className="mb-2" />
        <h3 className="text-sm font-semibold text-gray-900 line-clamp-2 mb-1 group-hover:text-cgiar-accent transition-colors">
          {tool.title}
        </h3>
        <p className="text-xs text-gray-500 line-clamp-3">
          {tool.summary}
        </p>
      </div>
    </button>
  );
}
