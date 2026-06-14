import { useEffect, useRef } from 'react';
import { AlertTriangle, Info, ThumbsUp, PenLine, Loader2 } from 'lucide-react';
import type { CandidateTool, ThreadItem } from '../../types/assistant';
import Markdown from './Markdown';
import SubagentPane from './SubagentPane';
import ToolChip from './ToolChip';
import ToolChips from './ToolChips';

interface ChatThreadProps {
  items: ThreadItem[];
  busy: boolean;
  onApprove: () => void;
  onRefine: () => void;
  /** Recommended/candidate tools from the live report draft (Item 2 deep-links). */
  candidateTools?: CandidateTool[];
}

/** The main conversation column: bubbles, subagent panes, tool chips, checkpoints. */
export default function ChatThread({ items, busy, onApprove, onRefine, candidateTools = [] }: ChatThreadProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const approveRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [items, busy]);

  // The acceptance checkpoint actions only show on the LAST result item, and
  // only when no turn is currently running.
  const lastResultId = [...items].reverse().find(i => i.kind === 'result')?.id;

  // Only surface tools the assistant still considers in play (not rejected),
  // and only those that carry a CGSpace handle id we can deep-link to.
  const relevantTools = candidateTools.filter(
    t => t.status !== 'rejected' && !!t.id,
  );

  // ── Accessibility: focus management on the acceptance checkpoint ──────────
  // When a checkpoint becomes actionable (turn finished + Approve/Refine shown),
  // move keyboard/screen-reader focus to the Approve button so the user is taken
  // to the decision they must make instead of having to hunt for it.
  const showCheckpointActions = !!lastResultId && !busy;
  useEffect(() => {
    if (showCheckpointActions) {
      approveRef.current?.focus();
    }
  }, [showCheckpointActions, lastResultId]);

  return (
    // role="log" + aria-live="polite" announces each streamed assistant/subagent
    // message and tool update to screen readers as it is appended. aria-busy is
    // toggled so assistive tech knows a turn is in progress.
    <div
      className="flex-1 overflow-y-auto px-1 py-3 space-y-1"
      role="log"
      aria-label="Assistant conversation"
      aria-live="polite"
      aria-relevant="additions text"
      aria-atomic="false"
      aria-busy={busy}
    >
      {/* Visually-hidden status region for the streaming state itself. */}
      <p className="sr-only" role="status">
        {busy ? 'The assistant is working on your challenge.' : ''}
      </p>
      {items.length === 0 && (
        <div className="text-center text-white/60 text-sm mt-10 px-6">
          <p className="text-white/90 text-base font-medium mb-2">
            Describe your scaling challenge
          </p>
          <p>
            The assistant will triage it, search the evidence base, and draft a
            recommendation report you can refine turn by turn.
          </p>
        </div>
      )}

      {items.map(item => {
        switch (item.kind) {
          case 'user':
            return (
              <div key={item.id} className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-md bg-cgiar-accent/20 border border-cgiar-accent/30 px-4 py-2.5">
                  <p className="text-sm text-white whitespace-pre-wrap">{item.text}</p>
                </div>
              </div>
            );

          case 'assistant_text':
            return (
              <div key={item.id} className="flex justify-start">
                <div className="max-w-[90%] rounded-2xl rounded-bl-md bg-white/10 border border-white/10 px-4 py-2.5">
                  <Markdown tone="dark">{item.text}</Markdown>
                </div>
              </div>
            );

          case 'subagent':
            return <SubagentPane key={item.id} item={item} />;

          case 'tool':
            return (
              <div key={item.id} className="pl-1">
                <ToolChip activity={item.activity} />
              </div>
            );

          case 'result': {
            const showActions = item.id === lastResultId && !busy;
            const checkpointLabel = `Acceptance checkpoint, turn ${item.turn}`;
            return (
              <div key={item.id} className="my-3">
                <div
                  className="rounded-2xl border border-cgiar-accent/40 bg-cgiar-green/30 px-4 py-3"
                  role="group"
                  aria-label={checkpointLabel}
                >
                  <div className="text-[11px] uppercase tracking-wide font-semibold text-cgiar-accent mb-1.5">
                    Acceptance checkpoint — turn {item.turn}
                  </div>
                  {item.event.final_text && (
                    <Markdown tone="dark">{item.event.final_text}</Markdown>
                  )}
                  {/* Deterministic catalog deep-link chips for the latest turn.
                      Independent of whether the model inlined markdown links. */}
                  {item.id === lastResultId && !busy && relevantTools.length > 0 && (
                    <ToolChips
                      tools={relevantTools.map(t => ({ id: t.id, title: t.title }))}
                    />
                  )}
                  {showActions && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        ref={approveRef}
                        onClick={onApprove}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-cgiar-accent text-cgiar-dark text-sm font-semibold px-4 py-2 hover:bg-green-400 transition-colors"
                      >
                        <ThumbsUp size={14} aria-hidden="true" />
                        Approve — proceed to drill-down
                      </button>
                      <button
                        onClick={onRefine}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-white/10 border border-white/25 text-white text-sm font-medium px-4 py-2 hover:bg-white/20 transition-colors"
                      >
                        <PenLine size={14} aria-hidden="true" />
                        Refine
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          }

          case 'error':
            return (
              <div key={item.id} className="flex justify-start">
                <div role="alert" className="max-w-[90%] rounded-xl bg-red-500/15 border border-red-400/40 px-4 py-2.5 flex items-start gap-2">
                  <AlertTriangle size={15} className="text-red-300 mt-0.5 shrink-0" aria-hidden="true" />
                  <p className="text-sm text-red-100">{item.message}</p>
                </div>
              </div>
            );

          case 'notice':
            return (
              <div key={item.id} className="flex justify-center">
                <div className="rounded-full bg-white/8 border border-white/15 px-3 py-1 flex items-center gap-1.5">
                  <Info size={12} className="text-white/50" aria-hidden="true" />
                  <span className="text-xs text-white/60">{item.text}</span>
                </div>
              </div>
            );

          default:
            return null;
        }
      })}

      {busy && (
        <div className="flex items-center gap-2 text-white/50 text-xs pl-2 pt-1">
          <Loader2 size={13} className="animate-spin" aria-hidden="true" />
          Working on your challenge…
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
