import { useState, useEffect, useRef, useCallback } from 'react';
import {
  X,
  ExternalLink,
  Share2,
  User,
  Calendar,
  Building2,
  Bookmark,
  Clock,
  FileInput,
  Monitor,
  Users,
  Landmark,
  Target,
  TrendingUp,
  BarChart3,
  MapPin,
  AlertTriangle,
  CheckCircle2,
  BookOpen,
  ChevronUp,
} from 'lucide-react';
import TypeBadge from '../common/TypeBadge';
import StarRating from './StarRating';
import LoadingSpinner from '../common/LoadingSpinner';
import { fetchTool, saveTool, unsaveTool } from '../../services/api';
import type { WikiToolDetail } from '../../types';
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

// ---------------------------------------------------------------------------
// Section heading component (colored left border accent)
// ---------------------------------------------------------------------------

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-sm font-semibold text-cgiar-dark uppercase tracking-wider mb-3 pl-3 border-l-4 border-cgiar-accent">
      {children}
    </h3>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface ToolDetailPanelProps {
  toolId: string;
  onClose: () => void;
  onToolViewed?: () => void;
}

export default function ToolDetailPanel({ toolId, onClose, onToolViewed }: ToolDetailPanelProps) {
  const [tool, setTool] = useState<WikiToolDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [isSaved, setIsSaved] = useState(() => getSavedTools().includes(toolId));
  const [saveBusy, setSaveBusy] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [showBackToTop, setShowBackToTop] = useState(false);

  // Track scroll position inside the modal
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      setShowBackToTop(container.scrollTop > 400);
    };

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, [tool]);

  const scrollToTop = () => {
    scrollContainerRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Close on Escape key + focus trap
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
      return;
    }

    // Focus trap: cycle focus within the modal
    if (e.key === 'Tab' && scrollContainerRef.current) {
      const focusable = scrollContainerRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }
  }, [onClose]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    // Focus the close button when modal opens
    closeButtonRef.current?.focus();
    // Prevent body scroll while modal is open
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
          setTool(data as WikiToolDetail);
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
      // Silently fail -- local state stays unchanged
    } finally {
      setSaveBusy(false);
    }
  };

  const bgColor = tool ? (TYPE_COLORS[tool.type] || '#607D8B') : '#607D8B';

  // Helper to check if wiki field has content
  const hasSteps = tool?.how_it_works_steps && tool.how_it_works_steps.length > 0;
  const hasDuration = !!tool?.how_it_works_duration;
  const hasInputs = !!tool?.how_it_works_inputs;
  const hasHowItWorks = hasSteps || hasDuration || hasInputs;

  const hasRequirements =
    !!tool?.requirements_technical ||
    !!tool?.requirements_human ||
    !!tool?.requirements_institutional;

  const hasOutcomes =
    !!tool?.expected_direct_outputs ||
    !!tool?.expected_impact ||
    !!tool?.expected_evidence;

  const hasExamples = tool?.practical_examples && tool.practical_examples.length > 0;
  const hasLimitations = !!tool?.limitations;
  const hasTakeaways = tool?.key_takeaways && tool.key_takeaways.length > 0;
  const hasCitation = !!tool?.full_citation;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-0 sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-label={tool ? `Tool details: ${tool.title}` : 'Tool details'}
      ref={modalRef}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-modal-backdrop"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div ref={scrollContainerRef} className="relative w-full h-full sm:max-w-3xl sm:max-h-[90vh] sm:rounded-2xl bg-white shadow-2xl overflow-y-auto animate-modal-content">
        {/* Close button */}
        <button
          ref={closeButtonRef}
          onClick={onClose}
          className="absolute top-4 right-4 z-10 w-10 h-10 bg-white/90 hover:bg-white rounded-full flex items-center justify-center shadow-md transition-colors"
          aria-label="Close tool details"
        >
          <X size={20} className="text-gray-600" aria-hidden="true" />
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
                className="w-full h-56 object-cover sm:rounded-t-2xl"
              />
            ) : (
              <div
                className="w-full h-56 flex items-center justify-center sm:rounded-t-2xl"
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
              <div className="flex flex-wrap gap-3 mb-6">
                {tool.authors.length > 0 && (
                  <div className="flex items-center gap-2 bg-gray-50 rounded-full px-3.5 py-1.5">
                    <div className="w-6 h-6 rounded-full bg-cgiar-accent/10 flex items-center justify-center">
                      <User size={12} className="text-cgiar-green" aria-hidden="true" />
                    </div>
                    <span className="text-sm text-gray-700">{tool.authors.slice(0, 3).join(', ')}{tool.authors.length > 3 ? ` +${tool.authors.length - 3} more` : ''}</span>
                  </div>
                )}
                {tool.date_published && (
                  <div className="flex items-center gap-2 bg-gray-50 rounded-full px-3.5 py-1.5">
                    <div className="w-6 h-6 rounded-full bg-blue-50 flex items-center justify-center">
                      <Calendar size={12} className="text-blue-600" aria-hidden="true" />
                    </div>
                    <span className="text-sm font-medium text-gray-700">{new Date(tool.date_published).getFullYear()}</span>
                  </div>
                )}
                {tool.source_organization && (
                  <div className="flex items-center gap-2 bg-gray-50 rounded-full px-3.5 py-1.5">
                    <div className="w-6 h-6 rounded-full bg-amber-50 flex items-center justify-center">
                      <Building2 size={12} className="text-amber-600" aria-hidden="true" />
                    </div>
                    <span className="text-sm text-gray-700">{tool.source_organization}</span>
                  </div>
                )}
              </div>

              {/* Summary */}
              <p className="text-gray-700 leading-relaxed mb-8">{tool.summary}</p>

              {/* Section Navigation */}
              {(() => {
                const sections: Array<{ id: string; label: string; available: boolean }> = [
                  { id: 'what-it-does', label: 'Overview', available: !!tool.what_it_does },
                  { id: 'how-it-works', label: 'How It Works', available: !!hasHowItWorks },
                  { id: 'requirements', label: 'Requirements', available: !!hasRequirements },
                  { id: 'outcomes', label: 'Outcomes', available: !!hasOutcomes },
                  { id: 'examples', label: 'Examples', available: !!hasExamples },
                  { id: 'takeaways', label: 'Takeaways', available: !!hasTakeaways },
                  { id: 'limitations', label: 'Limitations', available: !!hasLimitations },
                  { id: 'citation', label: 'Source', available: !!hasCitation },
                ];
                const available = sections.filter(s => s.available);
                if (available.length < 3) return null;
                return (
                  <nav aria-label="Tool sections" className="flex flex-wrap gap-1.5 mb-6 pb-4 border-b border-gray-100">
                    {available.map(s => (
                      <button
                        key={s.id}
                        onClick={() => {
                          const el = scrollContainerRef.current?.querySelector(`#section-${s.id}`);
                          el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }}
                        className="px-3 py-1 rounded-full bg-gray-100 hover:bg-cgiar-accent/10 hover:text-cgiar-green text-xs font-medium text-gray-600 transition-colors"
                      >
                        {s.label}
                      </button>
                    ))}
                  </nav>
                );
              })()}

              {/* Detail sections */}
              {tool.what_it_does && (
                <div id="section-what-it-does" className="mb-6">
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
                  {tool.when_to_use_it.includes('|') ? (
                    <div className="space-y-2">
                      {tool.when_to_use_it.split('|').map((part, i) => {
                        const trimmed = part.trim();
                        const colonIdx = trimmed.indexOf(':');
                        if (colonIdx > 0) {
                          const label = trimmed.slice(0, colonIdx).trim();
                          const value = trimmed.slice(colonIdx + 1).trim();
                          return (
                            <div key={i} className="flex items-start gap-2">
                              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider min-w-[80px] pt-0.5">{label}</span>
                              <span className="text-sm text-gray-600 leading-relaxed">{value}</span>
                            </div>
                          );
                        }
                        return <p key={i} className="text-sm text-gray-600 leading-relaxed">{trimmed}</p>;
                      })}
                    </div>
                  ) : (
                    <p className="text-gray-600 leading-relaxed">{tool.when_to_use_it}</p>
                  )}
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

              {/* ============================================================= */}
              {/* NEW WIKI PROFILE SECTIONS                                      */}
              {/* ============================================================= */}

              {/* How It Works */}
              {hasHowItWorks && (
                <div id="section-how-it-works" className="mb-8 pt-6 border-t border-gray-100">
                  <SectionHeading>How It Works</SectionHeading>

                  {/* Duration & Inputs row */}
                  {(hasDuration || hasInputs) && (
                    <div className="flex flex-wrap gap-4 mb-4">
                      {hasDuration && (
                        <div className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-2 text-sm text-gray-600">
                          <Clock size={14} className="text-cgiar-accent" aria-hidden="true" />
                          <span className="font-medium">Duration:</span> {tool!.how_it_works_duration}
                        </div>
                      )}
                      {hasInputs && (
                        <div className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-2 text-sm text-gray-600">
                          <FileInput size={14} className="text-cgiar-accent" aria-hidden="true" />
                          <span className="font-medium">Inputs:</span> {tool!.how_it_works_inputs}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Steps */}
                  {hasSteps && (
                    <ol className="space-y-2">
                      {tool!.how_it_works_steps!.map((step, i) => (
                        <li key={i} className="flex gap-3 text-gray-600 text-sm leading-relaxed">
                          <span className="flex-shrink-0 w-6 h-6 rounded-full bg-cgiar-accent/10 text-cgiar-green text-xs font-bold flex items-center justify-center mt-0.5">
                            {i + 1}
                          </span>
                          <span>{step}</span>
                        </li>
                      ))}
                    </ol>
                  )}
                </div>
              )}

              {/* What You'll Need (Requirements) */}
              {hasRequirements && (
                <div id="section-requirements" className="mb-8 pt-6 border-t border-gray-100">
                  <SectionHeading>What You'll Need</SectionHeading>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {tool!.requirements_technical && (
                      <div className="bg-gray-50 rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <Monitor size={14} className="text-blue-600" aria-hidden="true" />
                          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Technical</span>
                        </div>
                        <p className="text-sm text-gray-600 leading-relaxed">{tool!.requirements_technical}</p>
                      </div>
                    )}
                    {tool!.requirements_human && (
                      <div className="bg-gray-50 rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <Users size={14} className="text-green-600" aria-hidden="true" />
                          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Human</span>
                        </div>
                        <p className="text-sm text-gray-600 leading-relaxed">{tool!.requirements_human}</p>
                      </div>
                    )}
                    {tool!.requirements_institutional && (
                      <div className="bg-gray-50 rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <Landmark size={14} className="text-purple-600" aria-hidden="true" />
                          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Institutional</span>
                        </div>
                        <p className="text-sm text-gray-600 leading-relaxed">{tool!.requirements_institutional}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Expected Outcomes */}
              {hasOutcomes && (
                <div id="section-outcomes" className="mb-8 pt-6 border-t border-gray-100">
                  <SectionHeading>Expected Outcomes</SectionHeading>
                  <div className="space-y-4">
                    {tool!.expected_direct_outputs && (
                      <div className="flex gap-3">
                        <Target size={16} className="text-cgiar-accent flex-shrink-0 mt-0.5" aria-hidden="true" />
                        <div>
                          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-1">Direct Outputs</span>
                          <p className="text-sm text-gray-600 leading-relaxed">{tool!.expected_direct_outputs}</p>
                        </div>
                      </div>
                    )}
                    {tool!.expected_impact && (
                      <div className="flex gap-3">
                        <TrendingUp size={16} className="text-cgiar-accent flex-shrink-0 mt-0.5" aria-hidden="true" />
                        <div>
                          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-1">Intended Impact</span>
                          <p className="text-sm text-gray-600 leading-relaxed">{tool!.expected_impact}</p>
                        </div>
                      </div>
                    )}
                    {tool!.expected_evidence && (
                      <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
                        <div className="flex gap-3">
                          <BarChart3 size={16} className="text-emerald-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
                          <div>
                            <span className="text-xs font-semibold text-emerald-700 uppercase tracking-wider block mb-1">Evidence of Effectiveness</span>
                            <p className="text-sm text-emerald-800 leading-relaxed">{tool!.expected_evidence}</p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Practical Examples */}
              {hasExamples && (
                <div id="section-examples" className="mb-8 pt-6 border-t border-gray-100">
                  <SectionHeading>Practical Examples</SectionHeading>
                  <div className="space-y-4">
                    {tool!.practical_examples.map((example, i) => (
                      <div key={i} className="bg-gray-50 rounded-lg p-4 border border-gray-100">
                        {example.location && (
                          <div className="flex items-center gap-1.5 mb-2">
                            <MapPin size={12} className="text-orange-500" aria-hidden="true" />
                            <span className="text-xs font-semibold text-orange-600 uppercase tracking-wider">
                              {example.location}
                            </span>
                          </div>
                        )}
                        <p className="text-sm text-gray-600 leading-relaxed mb-2">
                          {example.description}
                        </p>
                        {example.key_result && (
                          <div className="bg-cgiar-accent/10 rounded px-3 py-2 text-sm text-cgiar-green font-medium">
                            Key result: {example.key_result}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Limitations */}
              {hasLimitations && (
                <div id="section-limitations" className="mb-8 pt-6 border-t border-gray-100">
                  <SectionHeading>Limitations</SectionHeading>
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                    <div className="flex gap-3">
                      <AlertTriangle size={16} className="text-amber-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
                      <p className="text-sm text-amber-800 leading-relaxed">{tool!.limitations}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Key Takeaways */}
              {hasTakeaways && (
                <div id="section-takeaways" className="mb-8 pt-6 border-t border-gray-100">
                  <SectionHeading>Key Takeaways</SectionHeading>
                  <ul className="space-y-2">
                    {tool!.key_takeaways.map((takeaway, i) => (
                      <li key={i} className="flex gap-2.5 text-sm text-gray-600 leading-relaxed">
                        <CheckCircle2 size={16} className="text-cgiar-accent flex-shrink-0 mt-0.5" aria-hidden="true" />
                        <span>{takeaway}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Source & Citation */}
              {hasCitation && (
                <div id="section-citation" className="mb-8 pt-6 border-t border-gray-100">
                  <SectionHeading>Source & Citation</SectionHeading>
                  <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
                    <div className="flex gap-3">
                      <BookOpen size={16} className="text-gray-500 flex-shrink-0 mt-0.5" aria-hidden="true" />
                      <p className="text-sm text-gray-600 leading-relaxed italic">{tool!.full_citation}</p>
                    </div>
                  </div>
                  {tool!.source_url && (
                    <a
                      href={tool!.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 mt-3 text-sm text-cgiar-accent hover:text-cgiar-green font-medium transition-colors"
                      aria-label={`View original source: ${tool!.title}`}
                    >
                      <ExternalLink size={14} aria-hidden="true" />
                      View original source
                    </a>
                  )}
                </div>
              )}

              {/* ============================================================= */}
              {/* END WIKI PROFILE SECTIONS                                      */}
              {/* ============================================================= */}

              {/* Footer: Source & Actions */}
              <div className="mt-8 pt-6 border-t border-gray-200">
                {/* Compact rating inline */}
                <div className="flex items-center justify-between mb-5">
                  <div className="flex items-center gap-3">
                    <StarRating
                      toolId={tool.id}
                      initialAverage={tool.average_rating}
                      initialCount={tool.rating_count}
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleToggleSave}
                      disabled={saveBusy}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                        isSaved
                          ? 'bg-cgiar-accent/10 text-cgiar-green'
                          : 'text-gray-500 hover:bg-gray-100'
                      }`}
                      aria-pressed={isSaved}
                      aria-label={isSaved ? 'Remove bookmark' : 'Bookmark this tool'}
                    >
                      <Bookmark size={14} className={isSaved ? 'fill-current' : ''} aria-hidden="true" />
                      {isSaved ? 'Saved' : 'Save'}
                    </button>
                    <button
                      onClick={handleShare}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-gray-500 hover:bg-gray-100 transition-colors"
                      aria-label={copied ? 'Link copied to clipboard' : 'Share tool link'}
                    >
                      <Share2 size={14} aria-hidden="true" />
                      {copied ? 'Copied!' : 'Share'}
                    </button>
                  </div>
                </div>

                {/* Visit resource -- clean text link, not a big button */}
                {tool.source_url && (
                  <a
                    href={tool.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center gap-2 w-full py-3 rounded-xl bg-cgiar-green/10 border border-cgiar-green/20 text-cgiar-green hover:bg-cgiar-green/20 font-medium text-sm transition-colors"
                    aria-label={`View original resource: ${tool.title}`}
                  >
                    <ExternalLink size={15} aria-hidden="true" />
                    View Original Resource on CG Space
                  </a>
                )}
              </div>
            </div>
          </>
        )}

        {/* Back to top */}
        {showBackToTop && (
          <button
            onClick={scrollToTop}
            className="sticky bottom-4 ml-auto mr-4 mb-2 w-10 h-10 rounded-full bg-white shadow-lg border border-gray-200 flex items-center justify-center hover:bg-gray-50 transition-colors z-10"
            aria-label="Scroll to top"
          >
            <ChevronUp size={18} className="text-gray-600" aria-hidden="true" />
          </button>
        )}
      </div>
    </div>
  );
}
