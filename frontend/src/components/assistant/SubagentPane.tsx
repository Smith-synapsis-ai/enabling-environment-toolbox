import { useState, useEffect } from 'react';
import { Bot, ChevronDown, ChevronRight, Loader2, CheckCircle2 } from 'lucide-react';
import type { ThreadItem } from '../../types/assistant';
import ToolChip from './ToolChip';
import Markdown from './Markdown';

type SubagentItem = Extract<ThreadItem, { kind: 'subagent' }>;

interface SubagentPaneProps {
  item: SubagentItem;
}

/**
 * Collapsible pane for one subagent invocation. Open while the subagent is
 * running (so users see live activity), collapses by default once finished.
 */
export default function SubagentPane({ item }: SubagentPaneProps) {
  // undefined = follow the auto behavior; true/false = user override
  const [userOpen, setUserOpen] = useState<boolean | undefined>(undefined);
  const open = userOpen !== undefined ? userOpen : !item.finished;

  // When the subagent finishes, drop back to auto (collapsed) unless the user
  // had explicitly opened it after finishing.
  useEffect(() => {
    if (item.finished) setUserOpen(undefined);
  }, [item.finished]);

  return (
    <div className="my-2 rounded-xl border border-cgiar-accent/25 bg-cgiar-green/20 overflow-hidden">
      <button
        onClick={() => setUserOpen(!open)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-white/5 transition-colors"
        aria-expanded={open}
      >
        <Bot size={16} className="text-cgiar-accent shrink-0" aria-hidden="true" />
        <span className="text-sm font-medium text-white/90 flex-1 truncate">
          Subagent: {item.subagentType}
        </span>
        {item.finished ? (
          <CheckCircle2 size={14} className="text-cgiar-accent" aria-label="finished" />
        ) : (
          <Loader2 size={14} className="animate-spin text-white/60" aria-label="running" />
        )}
        {open ? (
          <ChevronDown size={14} className="text-white/50" aria-hidden="true" />
        ) : (
          <ChevronRight size={14} className="text-white/50" aria-hidden="true" />
        )}
      </button>

      {open && (
        <div className="px-3 pb-3 border-t border-white/10">
          <div className="mt-2 text-xs text-white/50 italic line-clamp-3">
            Task: {item.prompt}
          </div>

          {item.toolCalls.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-x-2">
              {item.toolCalls.map(tc => (
                <ToolChip key={tc.toolUseId} activity={tc} compact />
              ))}
            </div>
          )}

          {item.texts.length > 0 && (
            <div className="mt-2 space-y-2">
              {item.texts.map((t, i) => (
                <Markdown key={i} tone="dark">{t}</Markdown>
              ))}
            </div>
          )}

          {!item.finished && item.texts.length === 0 && item.toolCalls.length === 0 && (
            <div className="mt-2 text-xs text-white/40">Working…</div>
          )}
        </div>
      )}
    </div>
  );
}
