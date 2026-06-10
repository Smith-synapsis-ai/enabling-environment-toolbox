// Task A6 — assistant REST helpers (separate from the static-mode mock api.ts;
// these hit the real backend through the Vite /api proxy).

import type { ReportDraftData } from '../types/assistant';

const SESSION_STORAGE_KEY = 'ee-assistant-session-id';

export function getAssistantSessionId(): string | null {
  return localStorage.getItem(SESSION_STORAGE_KEY);
}

export function setAssistantSessionId(sessionId: string): void {
  localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
}

export function clearAssistantSessionId(): void {
  localStorage.removeItem(SESSION_STORAGE_KEY);
}

export function newAssistantSessionId(): string {
  const id = crypto.randomUUID(); // MUST be a UUID — backend rejects others
  setAssistantSessionId(id);
  return id;
}

export async function fetchSessions(): Promise<string[]> {
  const res = await fetch('/api/assistant/sessions');
  if (!res.ok) {
    throw new Error(`Failed to list sessions (HTTP ${res.status})`);
  }
  const body = await res.json();
  return body.sessions as string[];
}

/** Returns the draft, or null if the session has no draft yet (404). */
export async function fetchDraft(sessionId: string): Promise<ReportDraftData | null> {
  const res = await fetch(`/api/assistant/sessions/${encodeURIComponent(sessionId)}/draft`);
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    throw new Error(`Failed to fetch draft (HTTP ${res.status})`);
  }
  return (await res.json()) as ReportDraftData;
}
