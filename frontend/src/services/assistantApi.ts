// Task A6 — assistant REST helpers (separate from the static-mode mock api.ts;
// these hit the real backend through the Vite /api proxy in dev, or directly
// via VITE_API_BASE_URL in production (Amplify CDN does not proxy /api calls).

import type { ReportDraftData } from '../types/assistant';

const SESSION_STORAGE_KEY = 'ee-assistant-session-id';

/**
 * Returns the absolute base URL for backend API calls.
 * In production, VITE_API_BASE_URL is set (e.g. https://api-ee-toolbox.synapsis-analytics.com)
 * and must be used because the Amplify CDN domain does not proxy /api/* to the backend.
 * In local dev, the empty string causes fetch() to use relative paths handled by Vite proxy.
 */
function apiBase(): string {
  return import.meta.env.VITE_API_BASE_URL || '';
}

// NOTE: sessionStorage (not localStorage) is intentional — per-tab isolation.
// localStorage is shared across all tabs in the same origin, which caused all
// tabs to reuse the same session ID and show identical conversations. Using
// sessionStorage gives each tab its own independent session from first load.
export function getAssistantSessionId(): string | null {
  return sessionStorage.getItem(SESSION_STORAGE_KEY);
}

export function setAssistantSessionId(sessionId: string): void {
  sessionStorage.setItem(SESSION_STORAGE_KEY, sessionId);
}

export function clearAssistantSessionId(): void {
  sessionStorage.removeItem(SESSION_STORAGE_KEY);
}

export function newAssistantSessionId(): string {
  const id = crypto.randomUUID(); // MUST be a UUID — backend rejects others
  setAssistantSessionId(id);
  return id;
}

export async function fetchSessions(): Promise<string[]> {
  const res = await fetch(`${apiBase()}/api/assistant/sessions`);
  if (!res.ok) {
    throw new Error(`Failed to list sessions (HTTP ${res.status})`);
  }
  const body = await res.json();
  return body.sessions as string[];
}

/** Returns the draft, or null if the session has no draft yet (404). */
export async function fetchDraft(sessionId: string): Promise<ReportDraftData | null> {
  const res = await fetch(`${apiBase()}/api/assistant/sessions/${encodeURIComponent(sessionId)}/draft`);
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    throw new Error(`Failed to fetch draft (HTTP ${res.status})`);
  }
  return (await res.json()) as ReportDraftData;
}

/** Upload a file to the backend and return its extracted text content. */
export async function uploadFile(file: File): Promise<string> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${apiBase()}/api/assistant/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    throw new Error(`Upload failed: ${res.status} ${res.statusText}`);
  }
  const data = await res.json() as { filename: string; content: string; char_count: number };
  return data.content;
}

/**
 * Download the report draft as PDF or Word doc.
 * Triggers a browser file download.
 */
export async function exportDraft(sessionId: string, format: 'pdf' | 'docx'): Promise<void> {
  const url = `${apiBase()}/api/assistant/sessions/${encodeURIComponent(sessionId)}/draft/export?format=${format}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Export failed: ${res.status} ${res.statusText}`);
  }
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = objectUrl;
  a.download = `scaling-report.${format === 'docx' ? 'docx' : 'pdf'}`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(objectUrl);
}
