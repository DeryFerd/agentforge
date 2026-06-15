/** MCP Server management page — register, test, and manage MCP servers. */

"use client";

import { useState, useEffect } from "react";
import { Server, Plus, Trash2, RefreshCw, CheckCircle, XCircle, GitBranch } from "lucide-react";
import api from "@/lib/api";

interface MCPServer {
  id: string;
  name: string;
  transport: string;
  url?: string;
  command?: string;
  health_status: string;
}

export default function MCPServersPage() {
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
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
    try {
      const response = await api.get(`/mcp-servers/${id}/health`);
      alert(`Health: ${JSON.stringify(response.data)}`);
    } catch {
      alert("Health check failed");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <header className="bg-white dark:bg-gray-900 border-b dark:border-gray-800">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-3">
          <a href="/" className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200">← Dashboard</a>
          <div className="w-8 h-8 bg-purple-600 rounded-lg flex items-center justify-center">
            <Server size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">MCP Servers</h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">Manage Model Context Protocol server connections</p>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        <div className="flex justify-between items-center mb-6">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            MCP servers provide tools that agents can call during workflow execution.
          </p>
          <button
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-1.5 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium"
          >
            <Plus size={14} /> Register Server
          </button>
        </div>

        {showForm && (
          <form onSubmit={handleSubmit} className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-4 mb-6 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Name</label>
                <input
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. web-search"
                  className="w-full px-3 py-2 border dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Transport</label>
                <select
                  value={form.transport}
                  onChange={(e) => setForm({ ...form, transport: e.target.value })}
                  className="w-full px-3 py-2 border dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 rounded-lg text-sm"
                >
                  <option value="stdio">stdio (local command)</option>
                  <option value="sse">SSE (remote URL)</option>
                </select>
              </div>
            </div>
            {form.transport === "stdio" ? (
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Command</label>
                <input
                  value={form.command}
                  onChange={(e) => setForm({ ...form, command: e.target.value })}
                  placeholder="e.g. npx -y @modelcontextprotocol/server-postgres postgresql://..."
                  className="w-full px-3 py-2 border dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 rounded-lg text-sm"
                />
              </div>
            ) : (
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">URL</label>
                <input
                  value={form.url}
                  onChange={(e) => setForm({ ...form, url: e.target.value })}
                  placeholder="http://localhost:3000/sse"
                  className="w-full px-3 py-2 border dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 rounded-lg text-sm"
                />
              </div>
            )}
            <div className="flex gap-2">
              <button type="submit" className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm">
                Register
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 bg-gray-100 dark:bg-gray-800 dark:text-gray-300 rounded-lg text-sm">
                Cancel
              </button>
            </div>
          </form>
        )}

        {loading ? (
          <div className="text-center py-12 text-gray-400 dark:text-gray-500">Loading...</div>
        ) : servers.length === 0 ? (
          <div className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-12 text-center">
            <Server size={32} className="text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <h3 className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">No MCP servers registered</h3>
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              Register an MCP server to make tools available to your agents.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {servers.map((server) => (
              <div key={server.id} className="bg-white dark:bg-gray-900 rounded-lg border dark:border-gray-700 p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Server size={18} className="text-purple-600 dark:text-purple-400" />
                  <div>
                    <h3 className="font-medium text-gray-800 dark:text-gray-200">{server.name}</h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {server.transport} — {server.url || server.command || "—"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`flex items-center gap-1 text-xs ${
                    server.health_status === "healthy" ? "text-green-600 dark:text-green-400" : "text-gray-400 dark:text-gray-500"
                  }`}>
                    {server.health_status === "healthy" ? <CheckCircle size={12} /> : <XCircle size={12} />}
                    {server.health_status}
                  </span>
                  <button
                    onClick={() => handleHealthCheck(server.id)}
                    className="p-1.5 text-gray-400 dark:text-gray-500 hover:text-blue-600 dark:hover:text-blue-400 rounded"
                  >
                    <RefreshCw size={14} />
                  </button>
                  <button
                    onClick={() => handleDelete(server.id)}
                    className="p-1.5 text-gray-400 dark:text-gray-500 hover:text-red-600 dark:hover:text-red-400 rounded"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
