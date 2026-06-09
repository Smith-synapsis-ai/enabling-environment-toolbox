import { useState, useEffect, useRef, useCallback } from 'react';
import { X, ExternalLink, Share2, User, Calendar, Building2, Bookmark } from 'lucide-react';
import TypeBadge from '../common/TypeBadge';
import StarRating from './StarRating';
import LoadingSpinner from '../common/LoadingSpinner';
import { fetchTool, saveTool, unsaveTool } from '../../services/api';
import type { ToolDetail } from '../../types';
import { TYPE_COLORS } from '../../types';

// ---------------------------------------------------------------------------
// Saved-tools localStorage helpers
// ---------------------------------------------------------------------------

const SAVED_TOOLS_KEY = 'ee-saved-tools';

function getSavedTools(): string[] {
  try {
    const raw = localStorage.getItem(SAVED_TOOLS_KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

function persistSavedTools(ids: string[]) {
  localStorage.setItem(SAVED_TOOLS_KEY, JSON.stringify(ids));
}

interface ToolDetailPanelProps {
  toolId: string;
  onClose: () => void;
  onToolViewed?: () => void;
}

export default function ToolDetailPanel({ toolId, onClose, onToolViewed }: ToolDetailPanelProps) {
  const [tool, setTool] = useState<ToolDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [isSaved, setIsSaved] = useState(() => getSavedTools().includes(toolId));
  const [saveBusy, setSaveBusy] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  // Close on Escape key
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  }, [onClose]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    // Focus the close button when panel opens
    closeButtonRef.current?.focus();
    // Prevent body scroll while panel is open
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [handleKeyDown]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchTool(toolId);
        if (!cancelled) {
          setTool(data);
          setLoading(false);
          onToolViewed?.();
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load tool');
          setLoading(false);
        }
      }
    }

    load();
    return () => { cancelled = true; };
  }, [toolId, onToolViewed]);

  const handleShare = async () => {
    const url = `${window.location.origin}/tool/${toolId}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
    }
  };

  const handleToggleSave = async () => {
    if (saveBusy) return;
    setSaveBusy(true);
    try {
      if (isSaved) {
        await unsaveTool(toolId);
        const updated = getSavedTools().filter(id => id !== toolId);
        persistSavedTools(updated);
        setIsSaved(false);
      } else {
        await saveTool(toolId);
        const updated = [...getSavedTools(), toolId];
        persistSavedTools(updated);
        setIsSaved(true);
      }
    } catch {
      // Silently fail — local state stays unchanged
    } finally {
      setSaveBusy(false);
    }
  };

  const bgColor = tool ? (TYPE_COLORS[tool.type] || '#607D8B') : '#607D8B';

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end"
      role="dialog"
      aria-modal="true"
      aria-label={tool ? `Tool details: ${tool.title}` : 'Tool details'}
      ref={panelRef}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div className="relative w-full lg:w-[60%] bg-white shadow-2xl overflow-y-auto animate-slide-in-right">
        {/* Close button */}
        <button
          ref={closeButtonRef}
          onClick={onClose}
          className="absolute top-4 right-4 z-10 w-10 h-10 bg-white/90 hover:bg-white rounded-full flex items-center justify-center shadow-md transition-colors"
          aria-label="Close tool details panel"
        >
          <X size={20} className="text-gray-600" />
        </button>

        {loading && (
          <div className="flex items-center justify-center h-96">
            <LoadingSpinner size={32} message="Loading tool details..." />
          </div>
        )}

        {error && (
          <div className="p-8">
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
              {error}
            </div>
          </div>
        )}

        {tool && (
          <>
            {/* Cover image or placeholder */}
            {tool.cover_image_url ? (
              <img
                src={tool.cover_image_url}
                alt={tool.title}
                className="w-full h-56 object-cover"
              />
            ) : (
              <div
                className="w-full h-56 flex items-center justify-center"
                style={{ backgroundColor: bgColor + '15' }}
              >
                <div
                  className="w-24 h-24 rounded-full flex items-center justify-center text-white text-3xl font-bold"
                  style={{ backgroundColor: bgColor }}
                >
                  {tool.title.charAt(0)}
                </div>
              </div>
            )}

            {/* Content */}
            <div className="p-6 sm:p-8">
              {/* Badge + title */}
              <TypeBadge type={tool.type} className="mb-3" />
              <h2 className="text-2xl font-bold text-gray-900 mb-2">{tool.title}</h2>

              {/* Metadata row */}
              <div className="flex flex-wrap gap-4 text-sm text-gray-500 mb-6">
                {tool.authors.length > 0 && (
                  <div className="flex items-center gap-1.5">
                    <User size={14} />
                    <span>{tool.authors.join(', ')}</span>
                  </div>
                )}
                {tool.date_published && (
                  <div className="flex items-center gap-1.5">
                    <Calendar size={14} />
                    <span>{new Date(tool.date_published).getFullYear()}</span>
                  </div>
                )}
                {tool.source_organization && (
                  <div className="flex items-center gap-1.5">
                    <Building2 size={14} />
                    <span>{tool.source_organization}</span>
                  </div>
                )}
              </div>

              {/* Summary */}
              <p className="text-gray-700 leading-relaxed mb-8">{tool.summary}</p>

              {/* Detail sections */}
              {tool.what_it_does && (
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-cgiar-dark uppercase tracking-wider mb-2">
                    What it does
                  </h3>
                  <p className="text-gray-600 leading-relaxed">{tool.what_it_does}</p>
                </div>
              )}

              {tool.when_to_use_it && (
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-cgiar-dark uppercase tracking-wider mb-2">
                    When to use it
                  </h3>
                  <p className="text-gray-600 leading-relaxed">{tool.when_to_use_it}</p>
                </div>
              )}

              {tool.who_its_for && (
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-cgiar-dark uppercase tracking-wider mb-2">
                    Who it's for
                  </h3>
                  <p className="text-gray-600 leading-relaxed">{tool.who_its_for}</p>
                </div>
              )}

              {/* Tags */}
              <div className="mb-6 space-y-3">
                {tool.pillars.length > 0 && (
                  <div>
                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Pillars: </span>
                    <div className="inline-flex flex-wrap gap-1.5 mt-1">
                      {tool.pillars.map(p => (
                        <span key={p} className="px-2 py-0.5 bg-cgiar-accent/10 text-cgiar-green text-xs rounded-full">
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {tool.domains.length > 0 && (
                  <div>
                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Domains: </span>
                    <div className="inline-flex flex-wrap gap-1.5 mt-1">
                      {tool.domains.map(d => (
                        <span key={d} className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded-full">
                          {d}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {tool.geography.length > 0 && (
                  <div>
                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Geography: </span>
                    <div className="inline-flex flex-wrap gap-1.5 mt-1">
                      {tool.geography.map(g => (
                        <span key={g} className="px-2 py-0.5 bg-orange-50 text-orange-700 text-xs rounded-full">
                          {g}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Rating */}
              <div className="mb-8 pt-4 border-t border-gray-100">
                <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-3">
                  Rate this tool
                </h3>
                <StarRating
                  toolId={tool.id}
                  initialAverage={tool.average_rating}
                  initialCount={tool.rating_count}
                />
              </div>

              {/* Action buttons */}
              <div className="flex gap-3">
                {tool.source_url && (
                  <a
                    href={tool.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-cgiar-accent hover:bg-cgiar-green text-white rounded-lg font-medium transition-colors"
                  >
                    <ExternalLink size={16} />
                    Visit Resource
                  </a>
                )}
                <button
                  onClick={handleToggleSave}
                  disabled={saveBusy}
                  className={`flex items-center justify-center gap-2 px-6 py-3 border rounded-lg font-medium transition-colors disabled:opacity-60 disabled:cursor-not-allowed ${
                    isSaved
                      ? 'border-cgiar-accent bg-cgiar-accent/10 text-cgiar-green hover:bg-cgiar-accent/20'
                      : 'border-gray-200 hover:bg-gray-50 text-gray-700'
                  }`}
                  aria-label={isSaved ? 'Remove bookmark' : 'Bookmark this tool'}
                  aria-pressed={isSaved}
                >
                  <Bookmark size={16} className={isSaved ? 'fill-current' : ''} />
                  {isSaved ? 'Saved' : 'Save'}
                </button>
                <button
                  onClick={handleShare}
                  className="flex items-center justify-center gap-2 px-6 py-3 border border-gray-200 hover:bg-gray-50 text-gray-700 rounded-lg font-medium transition-colors"
                >
                  <Share2 size={16} />
                  {copied ? 'Copied!' : 'Share'}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
