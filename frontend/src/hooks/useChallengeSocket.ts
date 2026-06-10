// Task A6 — WebSocket hook for the /ws/challenge endpoint.
//
// Maintains a persistent socket with exponential-backoff reconnect
// (1s -> 2s -> 4s ... capped at 30s, reset on successful open) and exposes
// the connection state plus a send function. Incoming frames are parsed and
// forwarded to the caller's handler (kept in a ref so re-renders never
// re-create the socket).

import { useCallback, useEffect, useRef, useState } from 'react';
import type { AssistantEvent, ConnectionState } from '../types/assistant';

const BACKOFF_BASE_MS = 1000;
const BACKOFF_CAP_MS = 30000;

function wsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.host}/ws/challenge`;
}

export interface ChallengeSocket {
  connectionState: ConnectionState;
  /** Send one challenge turn. Returns false if the socket is not open. */
  sendChallenge: (challengeText: string, sessionId: string) => boolean;
}

export function useChallengeSocket(
  onEvent: (event: AssistantEvent) => void,
): ChallengeSocket {
  const [connectionState, setConnectionState] = useState<ConnectionState>('connecting');
  const socketRef = useRef<WebSocket | null>(null);
  const onEventRef = useRef(onEvent);
  const attemptRef = useRef(0);
  const closedRef = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Always call the latest handler without re-opening the socket.
  onEventRef.current = onEvent;

  useEffect(() => {
    closedRef.current = false;

    const connect = () => {
      if (closedRef.current) return;
      setConnectionState(attemptRef.current === 0 ? 'connecting' : 'reconnecting');

      const ws = new WebSocket(wsUrl());
      socketRef.current = ws;

      ws.onopen = () => {
        attemptRef.current = 0; // reset backoff on success
        setConnectionState('open');
      };

      ws.onmessage = (msg: MessageEvent<string>) => {
        try {
          const event = JSON.parse(msg.data) as AssistantEvent;
          onEventRef.current(event);
        } catch {
          // Ignore malformed frames rather than crashing the stream.
        }
      };

      ws.onclose = () => {
        socketRef.current = null;
        if (closedRef.current) {
          setConnectionState('closed');
          return;
        }
        const delay = Math.min(
          BACKOFF_BASE_MS * 2 ** attemptRef.current,
          BACKOFF_CAP_MS,
        );
        attemptRef.current += 1;
        setConnectionState('reconnecting');
        timerRef.current = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        // onclose follows; reconnect handled there.
        ws.close();
      };
    };

    connect();

    return () => {
      closedRef.current = true;
      if (timerRef.current) clearTimeout(timerRef.current);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, []);

  const sendChallenge = useCallback((challengeText: string, sessionId: string): boolean => {
    const ws = socketRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return false;
    }
    ws.send(JSON.stringify({ challenge_text: challengeText, session_id: sessionId }));
    return true;
  }, []);

  return { connectionState, sendChallenge };
}
