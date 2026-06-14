import { useNavigate } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';

export interface ToolChipsTool {
  id: string;
  title: string;
}

interface ToolChipsProps {
  tools: ToolChipsTool[];
}

/**
 * Deterministic catalog deep-link chips.
 *
 * Renders one pill button per recommended/candidate tool, each navigating to
 * `/catalog?tool=<id>`. This is independent of whether the model inlined a
 * markdown link in its prose, so the user always gets a reliable way into the
 * catalog detail panel for every surfaced tool.
 */
export default function ToolChips({ tools }: ToolChipsProps) {
  const navigate = useNavigate();

  if (!tools || tools.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 mt-3" aria-label="Recommended tools — open in catalog">
      {tools.map(tool => (
        <button
          key={tool.id}
          type="button"
          onClick={() => navigate(`/catalog?tool=${encodeURIComponent(tool.id)}`)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-emerald-50 text-emerald-800 border border-emerald-200 hover:bg-emerald-100 hover:border-emerald-300 transition-colors cursor-pointer"
          title={`Open "${tool.title}" in the catalog`}
        >
          <ExternalLink size={13} aria-hidden="true" />
          {tool.title}
        </button>
      ))}
    </div>
  );
}
