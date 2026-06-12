/** Cost dashboard page — token usage and cost analytics. */

"use client";

import { useState, useEffect } from "react";
import { DollarSign, TrendingUp, BarChart3, GitBranch } from "lucide-react";
import api from "@/lib/api";

interface CostData {
  workspace_id: string;
  total_cost_usd: number;
  cost_by_model: Record<string, number>;
}

export default function CostPage() {
  const [data, setData] = useState<CostData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const workspaceId = typeof window !== "undefined" ? localStorage.getItem("current_workspace_id") || "default" : "default";

  useEffect(() => {
    const fetchCosts = async () => {
      try {
        const response = await api.get(`/costs/dashboard?workspace_id=${workspaceId}`);
        setData(response.data);
      } catch {
        setError("Could not load cost data");
      } finally {
        setLoading(false);
      }
    };
    fetchCosts();
  }, [workspaceId]);

  const modelEntries = data?.cost_by_model ? Object.entries(data.cost_by_model) : [];
  const maxCost = Math.max(...modelEntries.map(([, v]) => v as number), 0.001);

  const modelColors: Record<string, string> = {
    "gpt-4o": "bg-blue-500",
    "gpt-4o-mini": "bg-blue-400",
    "gpt-4.1": "bg-blue-600",
    "claude-sonnet-4-20250514": "bg-purple-500",
    "claude-3-5-haiku-20241022": "bg-purple-400",
    "gemini-2.0-flash": "bg-green-500",
    "gemini-2.5-pro": "bg-green-600",
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-3">
          <a href="/" className="text-sm text-gray-500 hover:text-gray-700">← Dashboard</a>
          <div className="w-8 h-8 bg-amber-600 rounded-lg flex items-center justify-center">
            <DollarSign size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Cost Dashboard</h1>
            <p className="text-xs text-gray-500">Token usage and cost analytics</p>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {error && (
          <div className="mb-4 text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</div>
        )}

        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading cost data...</div>
        ) : (
          <>
            {/* Summary cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
              <div className="bg-white rounded-lg border p-5">
                <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
                  <DollarSign size={14} />
                  Total Cost
                </div>
                <p className="text-3xl font-bold text-gray-900">
                  ${(data?.total_cost_usd || 0).toFixed(4)}
                </p>
              </div>
              <div className="bg-white rounded-lg border p-5">
                <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
                  <BarChart3 size={14} />
                  Models Used
                </div>
                <p className="text-3xl font-bold text-gray-900">
                  {modelEntries.length}
                </p>
              </div>
              <div className="bg-white rounded-lg border p-5">
                <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
                  <TrendingUp size={14} />
                  Projected Monthly
                </div>
                <p className="text-3xl font-bold text-gray-900">
                  ${((data?.total_cost_usd || 0) * 30).toFixed(2)}
                </p>
              </div>
            </div>

            {/* Cost by model chart */}
            <div className="bg-white rounded-lg border p-6 mb-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">Cost by Model</h2>
              {modelEntries.length === 0 ? (
                <p className="text-gray-400 text-sm text-center py-8">
                  No cost data yet. Run some workflows to see analytics.
                </p>
              ) : (
                <div className="space-y-3">
                  {modelEntries
                    .sort(([, a], [, b]) => (b as number) - (a as number))
                    .map(([model, cost]) => (
                      <div key={model} className="flex items-center gap-3">
                        <span className="text-sm text-gray-600 w-48 truncate font-mono">{model}</span>
                        <div className="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${modelColors[model] || "bg-gray-400"} flex items-center justify-end pr-2 transition-all`}
                            style={{ width: `${Math.max(((cost as number) / maxCost) * 100, 5)}%` }}
                          >
                            <span className="text-xs text-white font-medium">
                              ${(cost as number).toFixed(4)}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </div>

            {/* Pricing reference */}
            <div className="bg-white rounded-lg border p-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">Model Pricing Reference</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                {[
                  { model: "gpt-4o", input: "$2.50", output: "$10.00" },
                  { model: "gpt-4o-mini", input: "$0.15", output: "$0.60" },
                  { model: "claude-sonnet-4", input: "$3.00", output: "$15.00" },
                  { model: "gemini-2.0-flash", input: "$0.10", output: "$0.40" },
                ].map((p) => (
                  <div key={p.model} className="bg-gray-50 rounded-lg p-3">
                    <p className="font-mono text-xs text-gray-800 mb-1">{p.model}</p>
                    <p className="text-xs text-gray-500">In: {p.input} / Out: {p.output}</p>
                    <p className="text-xs text-gray-400">per 1M tokens</p>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
