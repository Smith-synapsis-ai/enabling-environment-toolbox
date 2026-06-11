/**
 * Lightweight anonymous event tracker for C3/C4 analytics.
 * Fire-and-forget: errors are silently swallowed (never interrupt the user).
 * No auth required — endpoint is public.
 *
 * NOTE: Must use VITE_API_BASE_URL (not a relative path) because in production
 * the frontend is served from Amplify CDN (ee-toolbox.synapsis-analytics.com)
 * which does NOT proxy /api/* — relative URLs would hit CloudFront and return
 * the SPA index.html rather than the backend. Same pattern as assistantApi.ts.
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export function trackEvent(
  name: string,
  payload?: Record<string, unknown>,
): void {
  const sessionId = sessionStorage.getItem('ee-assistant-session-id');
  fetch(`${API_BASE}/api/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      event_name: name,
      session_id: sessionId ?? undefined,
      payload: payload ?? undefined,
    }),
    keepalive: true,
  }).catch(() => {
    // Intentionally silent — analytics must never break the UI
  });
}
