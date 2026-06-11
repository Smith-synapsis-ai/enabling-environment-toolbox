/**
 * Lightweight anonymous event tracker for C3/C4 analytics.
 * Fire-and-forget: errors are silently swallowed (never interrupt the user).
 * No auth required — endpoint is public.
 */
export function trackEvent(
  name: string,
  payload?: Record<string, unknown>,
): void {
  const sessionId = sessionStorage.getItem('ee-assistant-session-id');
  fetch('/api/events', {
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
