/** Workspace setup page — create or select a workspace. */

"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { GitBranch, Plus, Building2 } from "lucide-react";
import { workspaceApi } from "@/lib/api";
import type { Workspace } from "@/lib/types";

export default function WorkspacesPage() {
  const router = useRouter();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [newName, setNewName] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchWorkspaces = async () => {
    try {
      const response = await workspaceApi.list();
      setWorkspaces(response.data);
    } catch {
      setError("Could not load workspaces — is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkspaces();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await workspaceApi.create(newName.trim());
      setNewName("");
      await fetchWorkspaces();
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const apiErr = err as { response?: { data?: { detail?: string } } };
        setError(apiErr.response?.data?.detail || "Failed to create workspace");
      } else {
        setError("Network error");
      }
    } finally {
      setCreating(false);
    }
  };

  const selectWorkspace = (ws: Workspace) => {
    localStorage.setItem("current_workspace_id", ws.id);
    localStorage.setItem("current_workspace_name", ws.name);
    router.push("/");
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <header className="bg-white dark:bg-gray-900 border-b dark:border-gray-800">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <GitBranch size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">Workspaces</h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">Manage your AgentForge workspaces</p>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-8">
        {/* Create workspace form */}
        <form onSubmit={handleCreate} className="flex gap-2 mb-6">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="New workspace name..."
            className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={creating || !newName.trim()}
            className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Plus size={14} />
            {creating ? "Creating..." : "Create"}
          </button>
        </form>

        {error && (
          <div className="mb-4 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30 px-3 py-2 rounded-lg">
            {error}
          </div>
        )}

        {/* Workspace list */}
        {loading ? (
          <div className="text-center py-12 text-gray-400 dark:text-gray-500">Loading workspaces...</div>
        ) : workspaces.length === 0 ? (
          <div className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-12 text-center">
            <Building2 size={32} className="text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <h3 className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">No workspaces yet</h3>
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              Create your first workspace to start building workflows.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {workspaces.map((ws) => (
              <button
                key={ws.id}
                onClick={() => selectWorkspace(ws)}
                className="w-full bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-4 text-left hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-sm transition-all"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-gray-800 dark:text-gray-200">{ws.name}</h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">ID: {ws.id}</p>
                  </div>
                  <span className="text-sm text-blue-600 dark:text-blue-400">Open →</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
