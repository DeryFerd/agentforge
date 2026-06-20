/** MCP Server management page â€” register, test, and manage MCP servers. */

"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Server, Plus, Trash2, RefreshCw, CheckCircle, XCircle, AlertCircle, Terminal, Globe } from "lucide-react";
import api from "@/lib/api";

interface MCPServer {
  id: string;
  name: string;
  transport: string;
  url?: string;
  command?: string;
  health_status: string;
}

const statusConfig: Record<string, { icon: React.ElementType; color: string; bg: string; label: string }> = {
  healthy: { icon: CheckCircle, color: "text-green-600 dark:text-green-400", bg: "bg-green-50 dark:bg-green-900/20", label: "Healthy" },
  configured: { icon: CheckCircle, color: "text-blue-600 dark:text-blue-400", bg: "bg-blue-50 dark:bg-blue-900/20", label: "Configured" },
  unhealthy: { icon: XCircle, color: "text-red-600 dark:text-red-400", bg: "bg-red-50 dark:bg-red-900/20", label: "Unhealthy" },
  unreachable: { icon: XCircle, color: "text-red-600 dark:text-red-400", bg: "bg-red-50 dark:bg-red-900/20", label: "Unreachable" },
  not_installed: { icon: AlertCircle, color: "text-yellow-600 dark:text-yellow-400", bg: "bg-yellow-50 dark:bg-yellow-900/20", label: "Not Installed" },
  unknown: { icon: AlertCircle, color: "text-gray-500 dark:text-gray-400", bg: "bg-gray-50 dark:bg-gray-800", label: "Unknown" },
};

export default function MCPServersPage() {
  const router = useRouter();
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [checkingId, setCheckingId] = useState<string | null>(null);
  const [healthDetails, setHealthDetails] = useState<Record<string, string>>({});
  const [form, setForm] = useState({
    workspace_id: "default",
    name: "",
    transport: "stdio",
    url: "",
    command: "",
  });

  const workspaceId = typeof window !== "undefined" ? localStorage.getItem("current_workspace_id") || "default" : "default";

  const fetchServers = async () => {
    try {
      const response = await api.get(`/mcp-servers?workspace_id=${workspaceId}`);
      setServers(response.data);
    } catch {
      console.error("Failed to fetch MCP servers");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchServers(); }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/mcp-servers", { ...form, workspace_id: workspaceId });
      setShowForm(false);
      setForm({ workspace_id: "default", name: "", transport: "stdio", url: "", command: "" });
      fetchServers();
    } catch (err) {
      console.error("Failed to register MCP server:", err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this MCP server?")) return;
    try {
      await api.delete(`/mcp-servers/${id}`);
      setServers((prev) => prev.filter((s) => s.id !== id));
    } catch {
      alert("Failed to delete");
    }
  };

  const handleHealthCheck = async (id: string) => {
    setCheckingId(id);
    try {
      const response = await api.get(`/mcp-servers/${id}/health`);
      setHealthDetails((prev) => ({ ...prev, [id]: response.data.detail || "" }));
      // Refresh server list to get updated health_status
      fetchServers();
    } catch {
      setHealthDetails((prev) => ({ ...prev, [id]: "Health check failed" }));
    } finally {
      setCheckingId(null);
    }
  };

  const checkAll = async () => {
    for (const s of servers) {
      await handleHealthCheck(s.id);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <header className="bg-white dark:bg-gray-900 border-b dark:border-gray-800">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <a href="/" className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200">â† Dashboard</a>
            <div className="w-8 h-8 bg-purple-600 rounded-lg flex items-center justify-center">
              <Server size={18} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">MCP Servers</h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">Manage Model Context Protocol server connections</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={checkAll}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-md transition-colors"
            >
              <RefreshCw size={14} /> Check All
            </button>
            <button
              onClick={() => setShowForm(!showForm)}
              className="flex items-center gap-1.5 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium"
            >
              <Plus size={14} /> Register Server
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
          MCP servers provide tools that agents can call during workflow execution.
          Register stdio (local) or SSE (remote) servers to enable tool use in your workflows.
        </p>

        {showForm && (
          <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-4 mb-6 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Name</label>
                <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. web-search" className="w-full px-3 py-2 border dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 rounded-lg text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Transport</label>
                <select value={form.transport} onChange={(e) => setForm({ ...form, transport: e.target.value })} className="w-full px-3 py-2 border dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 rounded-lg text-sm">
                  <option value="stdio">stdio (local command)</option>
                  <option value="sse">SSE (remote URL)</option>
                </select>
              </div>
            </div>
            {form.transport === "stdio" ? (
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Command</label>
                <input value={form.command} onChange={(e) => setForm({ ...form, command: e.target.value })} placeholder="e.g. npx -y @modelcontextprotocol/server-postgres postgresql://..." className="w-full px-3 py-2 border dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 rounded-lg text-sm" />
              </div>
            ) : (
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">URL</label>
                <input value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} placeholder="http://localhost:3000/sse" className="w-full px-3 py-2 border dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 rounded-lg text-sm" />
              </div>
            )}
            <div className="flex gap-2">
              <button type="submit" className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm">Register</button>
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 bg-gray-100 dark:bg-gray-800 dark:text-gray-300 rounded-lg text-sm">Cancel</button>
            </div>
          </form>
        )}

        {loading ? (
          <div className="text-center py-12 text-gray-400 dark:text-gray-500">Loading...</div>
        ) : servers.length === 0 ? (
          <div className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-12 text-center">
            <Server size={32} className="text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <h3 className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">No MCP servers registered</h3>
            <p className="text-gray-500 dark:text-gray-400 text-sm">Register an MCP server to make tools available to your agents.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {servers.map((server) => {
              const sc = statusConfig[server.health_status] || statusConfig.unknown;
              const StatusIcon = sc.icon;
              return (
                <div key={server.id} className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-5">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${sc.bg}`}>
                        {server.transport === "sse" ? <Globe size={20} className={sc.color} /> : <Terminal size={20} className={sc.color} />}
                      </div>
                      <div>
                        <h3 className="font-medium text-gray-800 dark:text-gray-200">{server.name}</h3>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${sc.bg} ${sc.color}`}>
                            <StatusIcon size={10} />
                            {sc.label}
                          </span>
                          <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">
                            {server.transport.toUpperCase()}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1.5 font-mono">
                          {server.transport === "sse" ? server.url : server.command}
                        </p>
                        {healthDetails[server.id] && (
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 italic">
                            {healthDetails[server.id]}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleHealthCheck(server.id)}
                        disabled={checkingId === server.id}
                        className="p-2 text-gray-400 dark:text-gray-500 hover:text-blue-600 dark:hover:text-blue-400 rounded transition-colors disabled:opacity-50"
                        title="Check health"
                      >
                        <RefreshCw size={14} className={checkingId === server.id ? "animate-spin" : ""} />
                      </button>
                      <button
                        onClick={() => handleDelete(server.id)}
                        className="p-2 text-gray-400 dark:text-gray-500 hover:text-red-600 dark:hover:text-red-400 rounded transition-colors"
                        title="Delete"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
