/** WebSocket hook for real-time execution events and HITL approval. */

import { useState, useEffect, useRef, useCallback } from "react";

export interface ExecutionEvent {
  type: "node_started" | "node_completed" | "node_failed" | "execution_paused" | "execution_resumed" | "execution_completed" | "execution_failed" | "pong";
  node_id?: string;
  node_name?: string;
  status?: string;
  data?: Record<string, unknown>;
  timestamp?: string;
}

interface UseWebSocketOptions {
  runId: string | null;
  onEvent?: (event: ExecutionEvent) => void;
  autoReconnect?: boolean;
}

interface UseWebSocketReturn {
  connected: boolean;
  events: ExecutionEvent[];
  lastEvent: ExecutionEvent | null;
  sendApproval: (nodeId: string, decision: "approved" | "rejected", feedback?: string) => void;
}

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export function useExecutionWebSocket({
  runId,
  onEvent,
  autoReconnect = true,
}: UseWebSocketOptions): UseWebSocketReturn {
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [lastEvent, setLastEvent] = useState<ExecutionEvent | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (!runId) return;

    const ws = new WebSocket(`${WS_URL}/ws/executions/${runId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      // Start ping interval
      const ping = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send("ping");
      }, 30000);
      ws.addEventListener("close", () => clearInterval(ping));
    };

    ws.onmessage = (e) => {
      try {
        const event: ExecutionEvent = JSON.parse(e.data);
        setLastEvent(event);
        setEvents((prev) => [...prev, event]);
        onEvent?.(event);
      } catch {
        // Ignore non-JSON messages (like pong responses)
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (autoReconnect) {
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [runId, onEvent, autoReconnect]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const sendApproval = useCallback(
    (nodeId: string, decision: "approved" | "rejected", feedback?: string) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            type: "hitl_response",
            node_id: nodeId,
            decision,
            feedback: feedback || null,
          })
        );
      }
    },
    []
  );

  return { connected, events, lastEvent, sendApproval };
}
