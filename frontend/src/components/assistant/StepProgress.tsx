import { Check, Loader2 } from 'lucide-react';
import type { StepFlags } from '../../types/assistant';

interface StepProgressProps {
  flags: StepFlags;
  busy: boolean;
}

const STEPS: { key: keyof StepFlags; label: string }[] = [
  { key: 'triage', label: 'Triage' },
  { key: 'evidenceSearch', label: 'Evidence search' },
  { key: 'reportDrafted', label: 'Report drafted' },
  { key: 'checkpoint', label: 'Acceptance checkpoint' },
  { key: 'drillDown', label: 'Drill-down' },
];

/**
 * Maps real orchestrator events onto a 5-step pathway indicator:
 * Triage = subagent_invocation, Evidence search = corpus_search tool_call,
 * Report drafted = report_update tool_call, Acceptance checkpoint = result
 * event, Drill-down = activity on turn >= 2.
 */
export default function StepProgress({ flags, busy }: StepProgressProps) {
  // The "active" step is the first incomplete one while a turn is running.
  const firstIncomplete = STEPS.findIndex(s => !flags[s.key]);

  return (
    <ol
      className="flex items-center gap-0 overflow-x-auto py-1 list-none m-0 p-0"
      aria-label="Pathway progress"
    >
      {STEPS.map((step, i) => {
        const done = flags[step.key];
        const active = busy && i === firstIncomplete;
        // Status word announced to screen readers (visually hidden) so each step
        // conveys completed / in-progress / not-started state, not just its label.
        const statusWord = done ? 'completed' : active ? 'in progress' : 'not started';
        return (
          <li
            key={step.key}
            className="flex items-center shrink-0"
            aria-current={active ? 'step' : undefined}
          >
            {i > 0 && (
              <div
                className={`h-px w-4 sm:w-8 ${done ? 'bg-cgiar-accent/70' : 'bg-white/20'}`}
                aria-hidden="true"
              />
            )}
            <div
              className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium border ${
                done
                  ? 'bg-cgiar-accent/20 border-cgiar-accent/50 text-white'
                  : active
                    ? 'bg-white/10 border-white/30 text-white/90'
                    : 'bg-transparent border-white/15 text-white/40'
              }`}
            >
              {done ? (
                <Check size={11} className="text-cgiar-accent" aria-hidden="true" />
              ) : active ? (
                <Loader2 size={11} className="animate-spin" aria-hidden="true" />
              ) : (
                <span className="w-[11px] text-center" aria-hidden="true">{i + 1}</span>
              )}
              <span>{step.label}</span>
              <span className="sr-only">: {statusWord}</span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
