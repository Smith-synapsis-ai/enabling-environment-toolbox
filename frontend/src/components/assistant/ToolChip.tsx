import { useState } from 'react';
import { Wrench, Search, FileEdit, FileText, ChevronDown, ChevronRight, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import type { ToolActivity } from '../../types/assistant';

function iconFor(shortName: string) {
  if (shortName.includes('corpus_search') || shortName.includes('search')) return Search;
  if (shortName.includes('report_update')) return FileEdit;
  if (shortName.includes('report_get') || shortName.includes('report_render')) return FileText;
  return Wrench;
}

function labelFor(shortName: string): string {
  const labels: Record<string, string> = {
    corpus_search: 'Evidence search',
    report_update: 'Report updated',
    report_get: 'Report read',
    report_render: 'Report rendered',
  };
  return labels[shortName] || shortName.replace(/_/g, ' ');
}

interface ToolChipProps {
  activity: ToolActivity;
  /** compact = inside subagent pane */
  compact?: boolean;
}

/** Compact chip for one tool call, expandable to show input/result detail. */
export default function ToolChip({ activity, compact = false }: ToolChipProps) {
  const [expanded, setExpanded] = useState(false);
  const Icon = iconFor(activity.shortName);
  const pending = !activity.result;
  const isError = activity.result?.isError === true;

  return (
    <div className={compact ? 'my-1' : 'my-1.5'}>
      <button
        onClick={() => setExpanded(!expanded)}
        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors border ${
          isError
            ? 'bg-red-500/15 border-red-400/40 text-red-200 hover:bg-red-500/25'
            : 'bg-white/8 border-white/15 text-white/75 hover:bg-white/15'
        }`}
        aria-expanded={expanded}
        title={activity.tool}
      >
        <Icon size={12} aria-hidden="true" />
        <span>{labelFor(activity.shortName)}</span>
        {pending ? (
          <Loader2 size={11} className="animate-spin text-white/50" aria-label="running" />
        ) : isError ? (
          <AlertCircle size={11} aria-label="error" />
        ) : (
          <CheckCircle2 size={11} className="text-cgiar-accent" aria-label="done" />
        )}
        {expanded ? <ChevronDown size={11} aria-hidden="true" /> : <ChevronRight size={11} aria-hidden="true" />}
      </button>

      {expanded && (
        <div className="mt-1 ml-2 rounded-md bg-black/30 border border-white/10 p-2 text-xs font-mono text-white/70 max-h-48 overflow-y-auto">
          <div className="text-white/40 mb-1">{activity.tool}</div>
          <div className="whitespace-pre-wrap break-words">
            {JSON.stringify(activity.input, null, 2)}
          </div>
          {activity.result && (
            <>
              <div className={`mt-2 mb-1 ${isError ? 'text-red-300' : 'text-white/40'}`}>
                {isError ? 'error result' : 'result'}
              </div>
              <div className="whitespace-pre-wrap break-words">
                {activity.result.text.slice(0, 1500)}
                {activity.result.text.length > 1500 ? ' …' : ''}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
