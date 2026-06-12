import { useCallback, useEffect, useRef, useState } from 'react';
import { FileText, MessageSquare, Plus, WifiOff } from 'lucide-react';
import { useChallengeSocket } from '../hooks/useChallengeSocket';
import {
  fetchDraft,
  getAssistantSessionId,
  newAssistantSessionId,
  setAssistantSessionId,
  uploadFile,
} from '../services/assistantApi';
import type {
  AssistantEvent,
  ReportDraftData,
  StepFlags,
  ThreadItem,
  ToolActivity,
} from '../types/assistant';
import { trackEvent } from '../services/trackEvent';
import ChatThread from '../components/assistant/ChatThread';
import ChatInput from '../components/assistant/ChatInput';
import ReportPanel from '../components/assistant/ReportPanel';
import StepProgress from '../components/assistant/StepProgress';

const APPROVE_MESSAGE =
  'I approve this pathway — please proceed with the evidence drill-down.';

const EMPTY_FLAGS: StepFlags = {
  triage: false,
  evidenceSearch: false,
  reportDrafted: false,
  checkpoint: false,
  drillDown: false,
};

/** mcp__ee__report_update -> report_update (tool names matched on SUFFIX). */
function shortToolName(tool: string): string {
  const parts = tool.split('__');
  return parts[parts.length - 1] || tool;
}

function resultText(content: unknown): string {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    return content
      .map(block =>
        block && typeof block === 'object' && 'text' in block
          ? String((block as { text: unknown }).text)
          : JSON.stringify(block),
      )
      .join('\n');
  }
  return JSON.stringify(content ?? '');
}

let _uid = 0;
function uid(prefix: string): string {
  _uid += 1;
  return `${prefix}-${Date.now()}-${_uid}`;
}

export default function AssistantPage() {
  const [items, setItems] = useState<ThreadItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [flags, setFlags] = useState<StepFlags>(EMPTY_FLAGS);
  const [draft, setDraft] = useState<ReportDraftData | null>(null);
  const [draftLoading, setDraftLoading] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);
  const [flash, setFlash] = useState(false);
  const [mobileView, setMobileView] = useState<'chat' | 'report'>('chat');
  const [refineSeq, setRefineSeq] = useState(0);

  const sessionIdRef = useRef<string>(getAssistantSessionId() || newAssistantSessionId());
  const turnRef = useRef(0); // logical user turns sent this browser session
  const toolNamesRef = useRef<Map<string, string>>(new Map()); // tool_use_id -> short name
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const flashTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const append = useCallback((item: ThreadItem) => {
    setItems(prev => [...prev, item]);
  }, []);

  // ----- report draft refresh -----------------------------------------------
  const refreshDraft = useCallback(async (withFlash = false) => {
    setDraftLoading(true);
    try {
      const data = await fetchDraft(sessionIdRef.current);
      setDraft(data);
      setDraftError(null);
      if (withFlash && data) {
        setFlash(true);
        if (flashTimerRef.current) clearTimeout(flashTimerRef.current);
        flashTimerRef.current = setTimeout(() => setFlash(false), 1200);
      }
    } catch (err) {
      setDraftError(err instanceof Error ? err.message : 'Failed to fetch report draft');
    } finally {
      setDraftLoading(false);
    }
  }, []);

  // ----- session resume on mount --------------------------------------------
  useEffect(() => {
    trackEvent('assistant_session_started');
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchDraft(sessionIdRef.current);
        if (cancelled) return;
        if (data) {
          setDraft(data);
          turnRef.current = data.turn_count;
          append({
            kind: 'notice',
            id: uid('notice'),
            text: `Resumed session (revision ${data.revision})`,
          });
          // A draft exists, so earlier turns already drafted a report.
          setFlags(f => ({ ...f, reportDrafted: true }));
        }
      } catch (err) {
        if (!cancelled) {
          setDraftError(err instanceof Error ? err.message : 'Failed to fetch report draft');
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ----- socket event handling ----------------------------------------------
  const handleEvent = useCallback((event: AssistantEvent) => {
    const drillDownNow = turnRef.current >= 2;

    switch (event.type) {
      case 'session_start':
        // The backend normalizes/echoes the logical session id — keep in sync.
        if (event.session_id && event.session_id !== sessionIdRef.current) {
          sessionIdRef.current = event.session_id;
          setAssistantSessionId(event.session_id);
        }
        break;

      case 'report_state':
        break; // revision surfaced via the draft panel instead

      case 'orchestrator_text':
        if (event.text.trim()) {
          append({ kind: 'assistant_text', id: uid('txt'), text: event.text });
        }
        break;

      case 'subagent_invocation':
        setFlags(f => ({ ...f, triage: true, drillDown: f.drillDown || drillDownNow }));
        append({
          kind: 'subagent',
          id: uid('sub'),
          toolUseId: event.tool_use_id,
          subagentType: event.subagent_type,
          prompt: event.prompt,
          texts: [],
          toolCalls: [],
          finished: false,
        });
        break;

      case 'subagent_text':
        if (!event.text.trim()) break;
        setItems(prev =>
          prev.map(item =>
            item.kind === 'subagent' && item.toolUseId === event.parent_tool_use_id
              ? { ...item, texts: [...item.texts, event.text] }
              : item,
          ),
        );
        break;

      case 'tool_call': {
        const short = shortToolName(event.tool);
        toolNamesRef.current.set(event.tool_use_id, short);
        if (short === 'corpus_search') {
          setFlags(f => ({ ...f, evidenceSearch: true, drillDown: f.drillDown || drillDownNow }));
        }
        if (short === 'report_update') {
          setFlags(f => ({ ...f, reportDrafted: true, drillDown: f.drillDown || drillDownNow }));
        }
        const activity: ToolActivity = {
          toolUseId: event.tool_use_id,
          tool: event.tool,
          shortName: short,
          input: event.input || {},
        };
        if (event.parent_tool_use_id) {
          // Nested inside a subagent pane.
          setItems(prev =>
            prev.map(item =>
              item.kind === 'subagent' && item.toolUseId === event.parent_tool_use_id
                ? { ...item, toolCalls: [...item.toolCalls, activity] }
                : item,
            ),
          );
        } else {
          append({ kind: 'tool', id: uid('tool'), activity });
        }
        break;
      }

      case 'tool_result': {
        const result = {
          isError: event.is_error === true,
          text: resultText(event.content),
        };
        setItems(prev =>
          prev.map(item => {
            // A result for a subagent's own tool_use_id means it finished.
            if (item.kind === 'subagent' && item.toolUseId === event.tool_use_id) {
              return { ...item, finished: true };
            }
            if (item.kind === 'subagent') {
              const idx = item.toolCalls.findIndex(tc => tc.toolUseId === event.tool_use_id);
              if (idx >= 0) {
                const toolCalls = [...item.toolCalls];
                toolCalls[idx] = { ...toolCalls[idx], result };
                return { ...item, toolCalls };
              }
              return item;
            }
            if (item.kind === 'tool' && item.activity.toolUseId === event.tool_use_id) {
              return { ...item, activity: { ...item.activity, result } };
            }
            return item;
          }),
        );
        // Refresh the live report panel after successful report writes.
        const short = toolNamesRef.current.get(event.tool_use_id);
        if (!event.is_error && (short === 'report_update' || short === 'report_render')) {
          void refreshDraft(true);
        }
        break;
      }

      case 'result':
        setFlags(f => ({ ...f, checkpoint: true, drillDown: f.drillDown || drillDownNow }));
        append({
          kind: 'result',
          id: uid('result'),
          event,
          turn: turnRef.current,
        });
        break;

      case 'turn_complete':
        trackEvent('challenge_completed');
        setBusy(false);
        // Mark any still-running subagents as finished (turn is over).
        setItems(prev =>
          prev.map(item =>
            item.kind === 'subagent' && !item.finished ? { ...item, finished: true } : item,
          ),
        );
        void refreshDraft(false);
        break;

      case 'error':
        append({ kind: 'error', id: uid('err'), message: event.message });
        break;
    }
  }, [append, refreshDraft]);

  const { connectionState, sendChallenge } = useChallengeSocket(handleEvent);

  // ----- actions -------------------------------------------------------------
  const sendTurn = useCallback((text: string) => {
    const ok = sendChallenge(text, sessionIdRef.current);
    if (!ok) {
      append({
        kind: 'error',
        id: uid('err'),
        message: 'Not connected to the assistant backend — message not sent. It will be possible to retry once the connection is restored.',
      });
      return;
    }
    turnRef.current += 1;
    append({ kind: 'user', id: uid('user'), text });
    setBusy(true);
  }, [append, sendChallenge]);

  const handleApprove = useCallback(() => {
    append({ kind: 'notice', id: uid('decision'), text: '✓ Pathway approved — proceeding to evidence drill-down' });
    sendTurn(APPROVE_MESSAGE);
  }, [append, sendTurn]);

  const handleRefine = useCallback(() => {
    append({ kind: 'notice', id: uid('decision'), text: '↩ Refinement requested — specify your changes in the box below' });
    setRefineSeq(s => s + 1);
  }, [append]);

  const handleNewSession = useCallback(() => {
    sessionIdRef.current = newAssistantSessionId();
    turnRef.current = 0;
    toolNamesRef.current.clear();
    setItems([]);
    setBusy(false);
    setFlags(EMPTY_FLAGS);
    setDraft(null);
    setDraftError(null);
  }, []);

  const handleAttach = useCallback(async (files: FileList) => {
    trackEvent('feature_file_upload');
    const fileArray = Array.from(files);
    const parts: string[] = [];
    for (const file of fileArray) {
      try {
        const content = await uploadFile(file);
        parts.push(`--- Attached file: ${file.name} ---\n${content}\n--- End of ${file.name} ---`);
      } catch {
        parts.push(`[Could not extract content from ${file.name} — please paste the relevant text directly]`);
      }
    }
    sendTurn(parts.join('\n\n'));
  }, [sendTurn]);

  // ----- degraded-state banner -----------------------------------------------
  const degraded =
    connectionState === 'reconnecting' || connectionState === 'closed'
      ? 'Assistant backend unreachable — reconnecting automatically. The page stays usable; recent results remain visible.'
      : draftError
        ? `Report draft could not be loaded (${draftError}). The conversation still works; the panel will refresh on the next update.`
        : null;

  const inputDisabled = busy || connectionState !== 'open';

  return (
    <div
      className="h-screen pt-16 flex flex-col bg-cgiar-dark"
      style={{
        backgroundImage:
          "linear-gradient(rgba(20,50,35,0.88), rgba(20,50,35,0.88)), url('/hero-bg.png')",
        backgroundSize: 'cover',
        backgroundPosition: 'center',
      }}
    >
      {/* Top bar: title + step progress + session controls */}
      <div className="shrink-0 px-4 sm:px-6 lg:px-8 pt-3 pb-2 border-b border-white/10">
        <div className="max-w-7xl mx-auto flex flex-col gap-2">
          <div className="flex items-center justify-between gap-3">
            <h1 className="text-white font-semibold text-base sm:text-lg">
              Scaling Challenge Assistant
            </h1>
            <div className="flex items-center gap-2">
              {/* Mobile report toggle */}
              <button
                onClick={() => setMobileView(v => (v === 'chat' ? 'report' : 'chat'))}
                className="lg:hidden inline-flex items-center gap-1.5 rounded-lg bg-white/10 border border-white/20 text-white text-xs font-medium px-3 py-1.5 hover:bg-white/20 transition-colors"
              >
                {mobileView === 'chat' ? (
                  <>
                    <FileText size={13} aria-hidden="true" /> Report
                    {draft && <span className="font-mono text-cgiar-accent">r{draft.revision}</span>}
                  </>
                ) : (
                  <>
                    <MessageSquare size={13} aria-hidden="true" /> Chat
                  </>
                )}
              </button>
              <button
                onClick={handleNewSession}
                className="inline-flex items-center gap-1.5 rounded-lg bg-white/10 border border-white/20 text-white text-xs font-medium px-3 py-1.5 hover:bg-white/20 transition-colors"
                title="Start a fresh session (new report draft)"
              >
                <Plus size={13} aria-hidden="true" /> New session
              </button>
            </div>
          </div>
          <StepProgress flags={flags} busy={busy} />
        </div>
      </div>

      {/* Degraded-state banner */}
      {degraded && (
        <div className="shrink-0 bg-amber-500/20 border-b border-amber-400/40 px-4 py-2">
          <div className="max-w-7xl mx-auto flex items-center gap-2">
            <WifiOff size={14} className="text-amber-300 shrink-0" aria-hidden="true" />
            <p className="text-xs text-amber-100">{degraded}</p>
          </div>
        </div>
      )}

      {/* Main two-column area */}
      <div className="flex-1 min-h-0 px-4 sm:px-6 lg:px-8 py-3">
        <div className="max-w-7xl mx-auto h-full flex gap-4">
          {/* Chat column */}
          <div
            className={`flex-col flex-1 min-w-0 ${
              mobileView === 'chat' ? 'flex' : 'hidden lg:flex'
            }`}
          >
            <ChatThread
              items={items}
              busy={busy}
              onApprove={handleApprove}
              onRefine={handleRefine}
            />
            <div className="shrink-0 pt-2 pb-1">
              <ChatInput
                disabled={inputDisabled}
                busy={busy}
                onSend={sendTurn}
                inputRef={inputRef}
                onAttach={handleAttach}
                prefill="Please refine the pathway by: "
                prefillSeq={refineSeq}
              />
              <p className="text-[10px] text-white/30 mt-1 px-1">
                Session {sessionIdRef.current.slice(0, 8)}… · {connectionState}
              </p>
            </div>
          </div>

          {/* Report panel: side panel on desktop, toggled view on mobile */}
          <div
            className={`lg:w-[420px] xl:w-[460px] w-full ${
              mobileView === 'report' ? 'block' : 'hidden lg:block'
            }`}
          >
            <ReportPanel draft={draft} loading={draftLoading} flash={flash} error={draftError} />
          </div>
        </div>
      </div>
    </div>
  );
}
