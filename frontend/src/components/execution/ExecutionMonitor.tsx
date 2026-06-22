/** Execution monitor panel — shows live WebSocket status and execution events. */

"use client";

import { useState, useCallback } from "react";
import { useExecutionWebSocket } from "@/lib/useExecutionWebSocket";
import { WebSocketStatus } from "./WebSocketStatus";
import { Loader2, CheckCircle, XCircle, AlertCircle, MessageSquare } from "lucide-react";
import type { ExecutionEvent } from "@/lib/useExecutionWebSocket";

interface ExecutionMonitorProps {
  runId: string | null;
}

const eventIcons: Record<string, React.ElementType> = {
  node_started: Loader2,
  node_completed: CheckCircle,
  node_failed: XCircle,
  execution_paused: AlertCircle,
  execution_resumed: CheckCircle,
  execution_completed: CheckCircle,
  execution_failed: XCircle,
};

const eventColors: Record<string, string> = {
  node_started: "text-blue-600 dark:text-blue-400",
  node_completed: "text-green-600 dark:text-green-400",
  node_failed: "text-red-600 dark:text-red-400",
  execution_paused: "text-yellow-600 dark:text-yellow-400",
  execution_resumed: "text-green-600 dark:text-green-400",
  execution_completed: "text-green-600 dark:text-green-400",
  execution_failed: "text-red-600 dark:text-red-400",
};

export function ExecutionMonitor({ runId }: ExecutionMonitorProps) {
  const [dismissedBanner, setDismissedBanner] = useState(false);

  const handleEvent = useCallback((event: ExecutionEvent) => {
    // Could trigger toasts or other UI updates here
    console.log("[ExecutionMonitor] Event:", event);
  }, []);

  const { connected, reconnectAttempts, lastEvent } = useExecutionWebSocket({
    runId,
    onEvent: handleEvent,
    autoReconnect: true,
  });

  if (!runId) return null;

  return (
    <div className="flex flex-col gap-3">
      {/* Connection status */}
      <WebSocketStatus
        runId={runId}
        connected={connected}
        reconnectAttempts={reconnectAttempts}
        onReconnect={() => {
          // Force reconnect by briefly disconnecting
          window.location.reload();
        }}
      />

      {/* Last event display */}
      {lastEvent && lastEvent.type !== "pong" && (
        <div className="flex items-start gap-2 p-2 rounded bg-gray-50 dark:bg-gray-800/50 border dark:border-gray-700">
          {(() => {
            const Icon = eventIcons[lastEvent.type] || MessageSquare;
            const color = eventColors[lastEvent.type] || "text-gray-500 dark:text-gray-400";
            return <Icon size={14} className={`${color} mt-0.5 flex-shrink-0`} />;
          })()}
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-gray-700 dark:text-gray-300 capitalize">
              {lastEvent.type.replace(/_/g, " ")}
            </p>
            {lastEvent.node_name && (
              <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                {lastEvent.node_name}
              </p>
            )}
            {lastEvent.timestamp && (
              <p className="text-xs text-gray-400 dark:text-gray-500">
                {new Date(lastEvent.timestamp).toLocaleTimeString()}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
