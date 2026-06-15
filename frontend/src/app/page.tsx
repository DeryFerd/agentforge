/** AgentForge Dashboard — workflow list and quick actions. */

"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Plus, GitBranch, Play, Settings, ExternalLink, LogIn, LogOut, Trash2, Clock, Server, Package, DollarSign, Key } from "lucide-react";
import { useWorkflowStore } from "@/stores/workflow-store";
import { workflowApi } from "@/lib/api";
import type { Workflow } from "@/lib/types";
import DarkModeToggle from "@/components/DarkModeToggle";

export default function DashboardPage() {
  const router = useRouter();
  const reset = useWorkflowStore((s) => s.reset);

  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  const currentWorkspace = typeof window !== "undefined" ? localStorage.getItem("current_workspace_id") : null;
  const workspaceName = typeof window !== "undefined" ? localStorage.getItem("current_workspace_name") : null;

  // Auth guard — redirect to login if not authenticated
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
    } else {
      setAuthChecked(true);
    }
  }, [router]);

  const fetchWorkflows = async () => {
    try {
      const response = await workflowApi.list(currentWorkspace || undefined);
      setWorkflows(response.data);
    } catch {
      setError("Could not load workflows — is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (authChecked) fetchWorkflows();
  }, [authChecked, currentWorkspace]);

  // Show nothing while auth is being checked (prevents flash)
  if (!authChecked) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
        <div className="text-gray-400 text-sm">Loading...</div>
      </div>
    );
  }

  const handleNewWorkflow = () => {
    reset();
    router.push("/editor");
  };

  const openWorkflow = (id: string) => {
    router.push(`/editor?id=${id}`);
  };

  const deleteWorkflow = async (id: string, name: string) => {
    if (!confirm(`Delete workflow "${name}"?`)) return;
    try {
      await workflowApi.delete(id);
      setWorkflows((prev) => prev.filter((w) => w.id !== id));
    } catch {
      alert("Failed to delete workflow");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("current_workspace_id");
    localStorage.removeItem("current_workspace_name");
    router.push("/login");
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Header */}
      <header className="bg-white dark:bg-gray-900 border-b dark:border-gray-800">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <GitBranch size={18} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">AgentForge</h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {workspaceName ? `Workspace: ${workspaceName}` : "Multi-Agent Workflow Orchestrator"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <a href="/workspaces" className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200">Workspaces</a>
            <a href="/templates" className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 flex items-center gap-1">
              <Package size={12} /> Templates
            </a>
            <a href="/mcp-servers" className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 flex items-center gap-1">
              <Server size={12} /> MCP
            </a>
            <a href="/cost" className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 flex items-center gap-1">
              <DollarSign size={12} /> Costs
            </a>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 flex items-center gap-1"
            >
              API <ExternalLink size={12} />
            </a>
            <a
              href="http://localhost:3001"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 flex items-center gap-1"
            >
              Langfuse <ExternalLink size={12} />
            </a>
            <DarkModeToggle />
            {authChecked ? (
              <button
                onClick={handleLogout}
                className="flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-red-600 transition-colors"
              >
                <LogOut size={14} /> Sign Out
              </button>
            ) : (
              <a
                href="/login"
                className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 transition-colors"
              >
                <LogIn size={14} /> Sign In
              </a>
            )}
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Stats cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-5">
            <p className="text-sm text-gray-500 dark:text-gray-400">Workflows</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">{workflows.length}</p>
          </div>
          <div className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-5">
            <p className="text-sm text-gray-500 dark:text-gray-400">Executions (24h)</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">—</p>
          </div>
          <div className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-5">
            <p className="text-sm text-gray-500 dark:text-gray-400">Cost (This Month)</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">
              <a href="/cost" className="hover:text-blue-600 dark:hover:text-blue-400">View →</a>
            </p>
          </div>
          <div className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-5">
            <p className="text-sm text-gray-500 dark:text-gray-400">MCP Servers</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">
              <a href="/mcp-servers" className="hover:text-purple-600 dark:hover:text-purple-400">Manage →</a>
            </p>
          </div>
        </div>

        {/* Workflows section */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200">Workflows</h2>
          <button
            onClick={handleNewWorkflow}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Plus size={16} />
            New Workflow
          </button>
        </div>

        {error && (
          <div className="mb-4 text-sm text-red-600 bg-red-50 dark:bg-red-900/30 dark:text-red-400 px-3 py-2 rounded-lg">{error}</div>
        )}

        {loading ? (
          <div className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-12 text-center text-gray-400 dark:text-gray-500">
            Loading workflows...
          </div>
        ) : workflows.length === 0 ? (
          /* Empty state */
          <div className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-12 text-center">
            <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
              <GitBranch size={28} className="text-gray-400 dark:text-gray-500" />
            </div>
            <h3 className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">No workflows yet</h3>
            <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto">
              Create your first multi-agent workflow. Design agents, connect them with edges,
              and execute them with full observability.
            </p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={handleNewWorkflow}
                className="inline-flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                <Plus size={16} />
                Create Workflow
              </button>
              <a
                href="/templates"
                className="inline-flex items-center gap-2 px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                <Package size={16} />
                Browse Templates
              </a>
            </div>
          </div>
        ) : (
          /* Workflow list */
          <div className="space-y-2">
            {workflows.map((wf) => (
              <div
                key={wf.id}
                className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-4 flex items-center justify-between hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-sm transition-all"
              >
                <button
                  onClick={() => openWorkflow(wf.id)}
                  className="flex-1 text-left"
                >
                  <h3 className="font-medium text-gray-800 dark:text-gray-200">{wf.name}</h3>
                  <div className="flex items-center gap-3 mt-1 text-xs text-gray-500 dark:text-gray-400">
                    <span>v{wf.version}</span>
                    <span className="flex items-center gap-1">
                      <Clock size={10} />
                      {new Date(wf.updated_at).toLocaleDateString()}
                    </span>
                    {wf.description && (
                      <span className="truncate max-w-xs">{wf.description}</span>
                    )}
                  </div>
                </button>
                <div className="flex items-center gap-2 ml-4">
                  <a
                    href={`/executions?workflow_id=${wf.id}`}
                    className="px-3 py-1.5 text-sm bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
                  >
                    History
                  </a>
                  <button
                    onClick={() => openWorkflow(wf.id)}
                    className="px-3 py-1.5 text-sm bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/50 rounded-md transition-colors"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => deleteWorkflow(wf.id, wf.name)}
                    className="p-1.5 text-gray-400 dark:text-gray-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-md transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Quick links */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-5">
            <div className="flex items-center gap-3 mb-3">
              <Play size={18} className="text-green-600" />
              <h3 className="font-medium text-gray-800 dark:text-gray-200">Quick Start</h3>
            </div>
            <ol className="text-sm text-gray-600 dark:text-gray-400 space-y-2 ml-7 list-decimal">
              <li>Click &quot;New Workflow&quot; to open the DAG editor</li>
              <li>Add nodes from the toolbar (Agent, Tool, Router, etc.)</li>
              <li>Connect nodes by dragging from output to input handles</li>
              <li>Click Validate to check your workflow</li>
              <li>Press Ctrl+S to save, or click Run to execute</li>
            </ol>
          </div>
          <div className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-5">
            <div className="flex items-center gap-3 mb-3">
              <Server size={18} className="text-purple-600" />
              <h3 className="font-medium text-gray-800 dark:text-gray-200">Tool Integration</h3>
            </div>
            <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-2 ml-7 list-disc">
              <li><a href="/mcp-servers" className="text-purple-600 hover:underline">Register MCP servers</a> for tool access</li>
              <li>Use Tool nodes in workflows to call MCP tools</li>
              <li>Supported: stdio (local) and SSE (remote) transports</li>
            </ul>
          </div>
          <div className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-5">
            <div className="flex items-center gap-3 mb-3">
              <Settings size={18} className="text-gray-600 dark:text-gray-400" />
              <h3 className="font-medium text-gray-800 dark:text-gray-200">Prerequisites</h3>
            </div>
            <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-2 ml-7 list-disc">
              <li>Backend: <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">localhost:8000</code></li>
              <li>PostgreSQL + Redis via Docker Compose</li>
              <li>LLM API key in <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">.env</code></li>
              <li>DB: <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">alembic upgrade head</code></li>
            </ul>
          </div>
        </div>
      </main>
    </div>
  );
}
