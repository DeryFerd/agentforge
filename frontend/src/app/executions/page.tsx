/** Execution history page — view past workflow runs and their traces. */

"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { GitBranch, Clock, CheckCircle, XCircle, AlertCircle, Pause, Loader2, ChevronDown, ChevronRight } from "lucide-react";
import { executionApi } from "@/lib/api";
import type { Execution } from "@/lib/types";

interface TraceNode {
  id: string;
  node_id: string;
  node_name: string;
  status: string;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  started_at: string | null;
  completed_at: string | null;
  error: { message: string } | null;
}

const statusConfig: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
  completed: { icon: CheckCircle, color: "text-green-600 dark:text-green-400", bg: "bg-green-50 dark:bg-green-900/20" },
  failed: { icon: XCircle, color: "text-red-600 dark:text-red-400", bg: "bg-red-50 dark:bg-red-900/20" },
  running: { icon: Loader2, color: "text-blue-600 dark:text-blue-400", bg: "bg-blue-50 dark:bg-blue-900/20" },
  paused: { icon: Pause, color: "text-yellow-600 dark:text-yellow-400", bg: "bg-yellow-50 dark:bg-yellow-900/20" },
  queued: { icon: Clock, color: "text-gray-500 dark:text-gray-400", bg: "bg-gray-50 dark:bg-gray-800" },
  cancelled: { icon: AlertCircle, color: "text-gray-500 dark:text-gray-400", bg: "bg-gray-50 dark:bg-gray-800" },
};

export default function ExecutionsPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
          <div className="text-gray-400 text-sm">Loading...</div>
        </div>
      }
    >
      <ExecutionsContent />
    </Suspense>
  );
}

function ExecutionsContent() {
  const searchParams = useSearchParams();
  const workflowId = searchParams.get("workflow_id");

  const [executions, setExecutions] = useState<Execution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [traceData, setTraceData] = useState<Record<string, TraceNode[]>>({});
  const [loadingTrace, setLoadingTrace] = useState<string | null>(null);

  useEffect(() => {
    const fetchExecutions = async () => {
      if (!workflowId) {
        setLoading(false);
        return;
      }
      try {
        const response = await executionApi.list(workflowId);
        setExecutions(response.data);
      } catch {
        setError("Could not load executions — is the backend running?");
      } finally {
        setLoading(false);
      }
    };
    fetchExecutions();
  }, [workflowId]);

  const loadTrace = async (runId: string) => {
    if (traceData[runId]) {
      setExpandedId(expandedId === runId ? null : runId);
      return;
    }
    setLoadingTrace(runId);
    try {
      const response = await executionApi.trace(runId);
      setTraceData((prev) => ({ ...prev, [runId]: response.data }));
      setExpandedId(runId);
    } catch {
      console.error("Failed to load trace");
    } finally {
      setLoadingTrace(null);
    }
  };

  const formatDuration = (started: string | null, completed: string | null) => {
    if (!started || !completed) return "—";
    const ms = new Date(completed).getTime() - new Date(started).getTime();
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Header */}
      <header className="bg-white dark:bg-gray-900 border-b dark:border-gray-800">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-3">
          <a href="/" className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200">
            ← Dashboard
          </a>
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <GitBranch size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">Execution History</h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {workflowId ? `Workflow: ${workflowId}` : "Select a workflow to view executions"}
            </p>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {error && (
          <div className="mb-4 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30 px-3 py-2 rounded-lg">{error}</div>
        )}

        {!workflowId ? (
          <div className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-12 text-center">
            <Clock size={32} className="text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <h3 className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">No workflow selected</h3>
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              Open a workflow in the editor and click the History button, or add{" "}
              <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">?workflow_id=YOUR_ID</code> to the URL.
            </p>
          </div>
        ) : loading ? (
          <div className="text-center py-12 text-gray-400 dark:text-gray-500">Loading executions...</div>
        ) : executions.length === 0 ? (
          <div className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-12 text-center">
            <Clock size={32} className="text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <h3 className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">No executions yet</h3>
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              Run this workflow from the editor to see execution history here.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {executions.map((exec) => {
              const sc = statusConfig[exec.status] || statusConfig.queued;
              const StatusIcon = sc.icon;
              const isExpanded = expandedId === exec.id;
              const trace = traceData[exec.id];

              return (
                <div key={exec.id} className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 overflow-hidden">
                  {/* Execution row */}
                  <button
                    onClick={() => loadTrace(exec.id)}
                    className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      {isExpanded ? (
                        <ChevronDown size={14} className="text-gray-400 dark:text-gray-500" />
                      ) : (
                        <ChevronRight size={14} className="text-gray-400 dark:text-gray-500" />
                      )}
                      <span className={`flex items-center gap-1.5 ${sc.color}`}>
                        <StatusIcon size={14} className={exec.status === "running" ? "animate-spin" : ""} />
                        <span className="text-sm font-medium capitalize">{exec.status}</span>
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {new Date(exec.created_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                      <span>Duration: {formatDuration(exec.created_at, exec.completed_at)}</span>
                      <span>Cost: ${exec.total_cost_usd.toFixed(4)}</span>
                      <span>{exec.trigger_type}</span>
                    </div>
                  </button>

                  {/* Expanded trace */}
                  {isExpanded && (
                    <div className="border-t dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 px-4 py-3">
                      {loadingTrace === exec.id ? (
                        <div className="flex items-center gap-2 text-sm text-gray-400 dark:text-gray-500">
                          <Loader2 size={14} className="animate-spin" />
                          Loading trace...
                        </div>
                      ) : trace && trace.length > 0 ? (
                        <div className="space-y-1">
                          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wide">
                            Node Execution Trace
                          </p>
                          {trace.map((node) => {
                            const nsc = statusConfig[node.status] || statusConfig.queued;
                            const NodeStatusIcon = nsc.icon;
                            return (
                              <div
                                key={node.id}
                                className={`flex items-center justify-between px-3 py-2 rounded text-sm ${nsc.bg}`}
                              >
                                <div className="flex items-center gap-2">
                                  <NodeStatusIcon
                                    size={12}
                                    className={nsc.color}
                                  />
                                  <span className="font-medium text-gray-800 dark:text-gray-200">{node.node_name}</span>
                                  <span className="text-xs text-gray-500 dark:text-gray-400">({node.node_id})</span>
                                </div>
                                <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                                  <span>Tokens: {node.tokens_in}→{node.tokens_out}</span>
                                  <span>${node.cost_usd.toFixed(4)}</span>
                                  <span>{formatDuration(node.started_at, node.completed_at)}</span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          No trace data available for this execution.
                        </p>
                      )}

                      {/* Error display */}
                      {exec.status === "failed" && (
                        <div className="mt-3 p-3 bg-red-50 dark:bg-red-900/30 rounded text-sm text-red-700 dark:text-red-400">
                          <strong>Execution Error:</strong>{" "}
                          {(exec as unknown as { error?: { message?: string } }).error?.message || "Unknown error"}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
