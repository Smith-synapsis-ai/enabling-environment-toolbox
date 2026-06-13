import { useState } from 'react';
import { Download, FileText, RefreshCw } from 'lucide-react';
import type { ReportDraftData } from '../../types/assistant';
import Markdown from './Markdown';
import { exportDraft, getAssistantSessionId } from '../../services/assistantApi';

interface ReportPanelProps {
  draft: ReportDraftData | null;
  loading: boolean;
  /** toggled briefly after a report_update result to flash the panel */
  flash: boolean;
  error: string | null;
}

const STATUS_STYLES: Record<string, string> = {
  accepted: 'bg-green-100 text-green-800 border-green-300',
  rejected: 'bg-red-100 text-red-700 border-red-300',
  candidate: 'bg-amber-50 text-amber-800 border-amber-300',
};

/** Live report-draft panel: rendered markdown + revision badge + tool status. */
export default function ReportPanel({ draft, loading, flash, error }: ReportPanelProps) {
  const [exporting, setExporting] = useState<'pdf' | 'docx' | null>(null);

  const handleExport = async (format: 'pdf' | 'docx') => {
    const sessionId = getAssistantSessionId();
    if (!sessionId || !draft) return;
    setExporting(format);
    try {
      await exportDraft(sessionId, format);
    } catch (err) {
      console.error('Export failed:', err);
      alert(`Download failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setExporting(null);
    }
  };

  return (
    <section
      className={`h-full flex flex-col rounded-2xl bg-white shadow-xl overflow-hidden transition-shadow duration-500 ${
        flash ? 'ring-4 ring-cgiar-accent shadow-cgiar-accent/40' : 'ring-1 ring-black/5'
      }`}
      aria-label="Report draft"
    >
      {/* Visually-hidden polite live region: announces each report-draft update
          (revision change) to screen-reader users without altering the layout. */}
      <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {draft ? `Report draft updated to revision ${draft.revision}.` : ''}
      </p>

      {/* Panel header */}
      <div className="flex items-center gap-2 px-4 py-3 bg-cgiar-dark text-white shrink-0">
        <FileText size={16} className="text-cgiar-accent" aria-hidden="true" />
        <h2 className="text-sm font-semibold flex-1">Report draft</h2>
        {loading && <RefreshCw size={14} className="animate-spin text-white/60" aria-label="refreshing" />}
        {draft && (
          <span
            className={`text-[11px] font-mono rounded-full px-2 py-0.5 border ${
              flash ? 'bg-cgiar-accent text-cgiar-dark border-cgiar-accent' : 'bg-white/10 border-white/20'
            }`}
          >
            rev {draft.revision}
          </span>
        )}
        {draft && (
          <div className="flex items-center gap-1 ml-auto">
            <button
              onClick={() => handleExport('pdf')}
              disabled={!!exporting}
              className="flex items-center gap-1 text-[11px] font-medium px-2 py-1 rounded-md bg-white/10 hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-white"
              title="Download as PDF"
            >
              {exporting === 'pdf' ? (
                <RefreshCw size={11} className="animate-spin" />
              ) : (
                <Download size={11} />
              )}
              PDF
            </button>
            <button
              onClick={() => handleExport('docx')}
              disabled={!!exporting}
              className="flex items-center gap-1 text-[11px] font-medium px-2 py-1 rounded-md bg-white/10 hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-white"
              title="Download as Word document"
            >
              {exporting === 'docx' ? (
                <RefreshCw size={11} className="animate-spin" />
              ) : (
                <Download size={11} />
              )}
              Word
            </button>
          </div>
        )}
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4">
        {error && (
          <div className="mb-3 rounded-md bg-red-50 border border-red-200 text-red-700 text-xs p-2">
            {error}
          </div>
        )}

        {!draft && !error && (
          <p className="text-sm text-gray-500 italic mt-4 text-center">
            No report draft yet — describe your scaling challenge to start one.
          </p>
        )}

        {draft && (
          <>
            {/* Candidate tools status list */}
            {draft.candidate_tools.length > 0 && (
              <div className="mb-4">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1.5">
                  Candidate tools
                </h3>
                <ul className="space-y-1">
                  {draft.candidate_tools.map(t => (
                    <li key={t.id} className="flex items-center gap-2 text-sm">
                      <span
                        className={`text-[10px] font-medium uppercase rounded-full border px-1.5 py-0.5 ${
                          STATUS_STYLES[t.status] || STATUS_STYLES.candidate
                        }`}
                      >
                        {t.status}
                      </span>
                      <span className="text-gray-700 truncate">{t.title}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <Markdown tone="light">{draft.rendered_markdown}</Markdown>

            {draft.changelog.length > 0 && (
              <div className="mt-4 pt-3 border-t border-gray-100">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1.5">
                  Changelog
                </h3>
                <ul className="space-y-0.5">
                  {draft.changelog.slice(-5).reverse().map(c => (
                    <li key={c.revision} className="text-xs text-gray-500">
                      <span className="font-mono text-gray-400">r{c.revision}</span> — {c.summary}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}
