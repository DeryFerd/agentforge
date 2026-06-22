/** WebSocket connection status indicator with auto-reconnect and user notification. */

"use client";

import { useState, useEffect } from "react";
import { Wifi, WifiOff, AlertTriangle, RefreshCw } from "lucide-react";

interface WebSocketStatusProps {
  runId: string | null;
  connected: boolean;
  reconnectAttempts: number;
  onReconnect?: () => void;
}

export function WebSocketStatus({
  runId,
  connected,
  reconnectAttempts,
  onReconnect,
}: WebSocketStatusProps) {
  const [showDismissed, setShowDismissed] = useState(false);
  const [showBanner, setShowBanner] = useState(false);

  // Show banner after 2 seconds of disconnection
  useEffect(() => {
    if (!connected && runId) {
      const timer = setTimeout(() => {
        setShowBanner(true);
      }, 2000);
      return () => clearTimeout(timer);
    } else {
      setShowBanner(false);
      setShowDismissed(false);
    }
  }, [connected, runId]);

  // Auto-hide banner if connection restored
  useEffect(() => {
    if (connected) {
      setShowDismissed(false);
    }
  }, [connected]);

  if (!runId) return null;
  if (connected) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-green-600 dark:text-green-400">
        <Wifi size={12} />
        <span>Live</span>
      </div>
    );
  }

  if (showBanner && !showDismissed) {
    const maxAttempts = 5;
    const isExcessive = reconnectAttempts > maxAttempts;

    return (
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
        {isExcessive ? (
          <AlertTriangle size={14} className="text-amber-600 dark:text-amber-400 flex-shrink-0" />
        ) : (
          <RefreshCw size={14} className="text-amber-600 dark:text-amber-400 flex-shrink-0 animate-spin" />
        )}
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-amber-800 dark:text-amber-200">
            {isExcessive
              ? "Connection lost — reconnecting failed"
              : `Connection lost${reconnectAttempts > 0 ? ` (attempt ${reconnectAttempts})` : ""}…`}
          </p>
          <p className="text-xs text-amber-600 dark:text-amber-400 mt-0.5">
            {isExcessive
              ? "Check your network or reload the page"
              : "Attempting to reconnect automatically"}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {isExcessive && onReconnect && (
            <button
              onClick={onReconnect}
              className="text-xs px-2 py-1 rounded bg-amber-200 dark:bg-amber-800 hover:bg-amber-300 dark:hover:bg-amber-700 text-amber-900 dark:text-amber-100 transition-colors"
              title="Try reconnecting now"
            >
              Retry
            </button>
          )}
          <button
            onClick={() => setShowDismissed(true)}
            className="text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-200 transition-colors"
            title="Dismiss this notification"
          >
            ×
          </button>
        </div>
      </div>
    );
  }

  // Dismissed state — show subtle indicator only
  return (
    <div className="flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-400" title="Disconnected — events may be delayed">
      <WifiOff size={12} />
      <span>Offline</span>
    </div>
  );
}
