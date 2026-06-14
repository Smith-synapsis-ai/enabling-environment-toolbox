// ---------------------------------------------------------------------------
// Task A6 — Conversational Assistant types
//
// Event vocabulary mirrors backend/agents/orchestrator.py (source of truth)
// plus the two server-side frames added by backend/app/routers/assistant.py
// (turn_complete, error).
// ---------------------------------------------------------------------------

export interface SessionStartEvent {
  type: 'session_start';
  session_id: string;
  orchestrator_model: string;
  subagent_model: string;
  prompt_sources?: Record<string, unknown>;
}

export interface ReportStateEvent {
  type: 'report_state';
  session_id: string;
  revision: number;
  turn: number;
  exists: boolean;
}

export interface OrchestratorTextEvent {
  type: 'orchestrator_text';
  text: string;
}

export interface SubagentInvocationEvent {
  type: 'subagent_invocation';
  tool_use_id: string;
  subagent_type: string;
  prompt: string;
}

export interface SubagentTextEvent {
  type: 'subagent_text';
  parent_tool_use_id: string;
  text: string;
}

export interface ToolCallEvent {
  type: 'tool_call';
  tool_use_id: string;
  tool: string;
  input: Record<string, unknown>;
  parent_tool_use_id: string | null;
}

export interface ToolResultEvent {
  type: 'tool_result';
  tool_use_id: string;
  content: unknown;
  is_error: boolean;
}

export interface ResultEvent {
  type: 'result';
  // NOTE: this session_id is SDK-internal, NOT the logical session id.
  session_id: string;
  is_error: boolean;
  duration_ms: number;
  num_turns: number;
  total_cost_usd: number;
  usage: Record<string, unknown>;
  final_text: string;
}

export interface TurnCompleteEvent {
  type: 'turn_complete';
}

export interface GenerationCancelledEvent {
  type: 'generation_cancelled';
  session_id: string;
}

export interface ServerErrorEvent {
  type: 'error';
  message: string;
}

export type AssistantEvent =
  | SessionStartEvent
  | ReportStateEvent
  | OrchestratorTextEvent
  | SubagentInvocationEvent
  | SubagentTextEvent
  | ToolCallEvent
  | ToolResultEvent
  | ResultEvent
  | TurnCompleteEvent
  | GenerationCancelledEvent
  | ServerErrorEvent;

// ---------------------------------------------------------------------------
// Report draft (GET /api/assistant/sessions/{id}/draft)
// ---------------------------------------------------------------------------

export interface ReportSection {
  id: string;
  heading: string;
  body_md: string;
  sources: string[];
}

export interface CandidateTool {
  id: string;
  title: string;
  status: string; // candidate | accepted | rejected
}

export interface ChangelogEntry {
  revision: number;
  turn: number;
  summary: string;
}

export interface ReportDraftData {
  session_id: string;
  schema_version: number;
  title: string;
  challenge_summary: string;
  sections: ReportSection[];
  candidate_tools: CandidateTool[];
  revision: number;
  turn_count: number;
  updated_at: string;
  changelog: ChangelogEntry[];
  rendered_markdown: string;
}

// ---------------------------------------------------------------------------
// UI thread model
// ---------------------------------------------------------------------------

export interface ToolActivity {
  toolUseId: string;
  tool: string; // full MCP name, e.g. mcp__ee__report_update
  shortName: string; // suffix, e.g. report_update
  input: Record<string, unknown>;
  result?: { isError: boolean; text: string };
}

export type ThreadItem =
  | { kind: 'user'; id: string; text: string }
  | { kind: 'assistant_text'; id: string; text: string }
  | {
      kind: 'subagent';
      id: string;
      toolUseId: string;
      subagentType: string;
      prompt: string;
      texts: string[];
      toolCalls: ToolActivity[];
      finished: boolean;
    }
  | { kind: 'tool'; id: string; activity: ToolActivity }
  | { kind: 'result'; id: string; event: ResultEvent; turn: number }
  | { kind: 'error'; id: string; message: string }
  | { kind: 'notice'; id: string; text: string };

export type ConnectionState = 'connecting' | 'open' | 'reconnecting' | 'closed';

export interface StepFlags {
  triage: boolean; // subagent_invocation seen
  evidenceSearch: boolean; // corpus_search tool_call seen
  reportDrafted: boolean; // report_update tool_call seen
  checkpoint: boolean; // result event seen
  drillDown: boolean; // turn >= 2 activity
}
