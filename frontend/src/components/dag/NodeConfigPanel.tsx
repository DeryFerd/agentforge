/** Node configuration sidebar panel — shown when a node is selected. */

"use client";

import { useWorkflowStore } from "@/stores/workflow-store";
import { X } from "lucide-react";

export default function NodeConfigPanel() {
  const { nodes, selectedNodeId, isPanelOpen, selectNode, updateNodeData } = useWorkflowStore();

  if (!isPanelOpen || !selectedNodeId) return null;

  const node = nodes.find((n) => n.id === selectedNodeId);
  if (!node) return null;

  const nodeType = (node.data?.nodeType as string) || "agent";
  const label = (node.data?.label as string) || "";
  const config = (node.data?.config as Record<string, unknown>) || {};

  const updateField = (key: string, value: unknown) => {
    updateNodeData(selectedNodeId, {
      config: { ...config, [key]: value },
    });
  };

  const updateLabel = (newLabel: string) => {
    updateNodeData(selectedNodeId, { label: newLabel });
  };

  const close = () => selectNode(null);

  return (
    <div className="absolute top-0 right-0 h-full w-80 bg-white border-l shadow-lg z-30 overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b sticky top-0 bg-white">
        <div>
          <h3 className="text-sm font-semibold text-gray-800">Node Configuration</h3>
          <p className="text-xs text-gray-500 capitalize">{nodeType} node</p>
        </div>
        <button
          onClick={close}
          className="p-1 text-gray-400 hover:text-gray-600 rounded"
        >
          <X size={16} />
        </button>
      </div>

      {/* Config form */}
      <div className="p-4 space-y-4">
        {/* Label */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
          <input
            type="text"
            value={label}
            onChange={(e) => updateLabel(e.target.value)}
            className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {/* Agent Node Config */}
        {nodeType === "agent" && (
          <>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">System Prompt</label>
              <textarea
                value={(config.system_prompt as string) || ""}
                onChange={(e) => updateField("system_prompt", e.target.value)}
                rows={4}
                placeholder="You are a helpful assistant..."
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 resize-y"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Model Provider</label>
              <select
                value={((config.model as Record<string, unknown>)?.provider as string) || "openai"}
                onChange={(e) =>
                  updateField("model", {
                    ...(config.model as Record<string, unknown>),
                    provider: e.target.value,
                  })
                }
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="google">Google</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Model ID</label>
              <input
                type="text"
                value={((config.model as Record<string, unknown>)?.model_id as string) || ""}
                onChange={(e) =>
                  updateField("model", {
                    ...(config.model as Record<string, unknown>),
                    model_id: e.target.value,
                  })
                }
                placeholder="gpt-4o-mini"
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Temperature</label>
              <input
                type="number"
                min={0}
                max={2}
                step={0.1}
                value={((config.model as Record<string, unknown>)?.temperature as number) ?? 0.3}
                onChange={(e) =>
                  updateField("model", {
                    ...(config.model as Record<string, unknown>),
                    temperature: parseFloat(e.target.value),
                  })
                }
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </>
        )}

        {/* Tool Node Config */}
        {nodeType === "tool" && (
          <>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">MCP Server</label>
              <input
                type="text"
                value={((config.tool as Record<string, unknown>)?.server as string) || ""}
                onChange={(e) =>
                  updateField("tool", {
                    ...(config.tool as Record<string, unknown>),
                    server: e.target.value,
                  })
                }
                placeholder="e.g. web-search"
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Tool Name</label>
              <input
                type="text"
                value={((config.tool as Record<string, unknown>)?.tool as string) || ""}
                onChange={(e) =>
                  updateField("tool", {
                    ...(config.tool as Record<string, unknown>),
                    tool: e.target.value,
                  })
                }
                placeholder="e.g. search"
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </>
        )}

        {/* Router Node Config */}
        {nodeType === "router" && (
          <>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Routing Mode</label>
              <select
                value={(config.routing_mode as string) || "conditional"}
                onChange={(e) => updateField("routing_mode", e.target.value)}
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="conditional">Conditional</option>
                <option value="llm_based">LLM-Based</option>
                <option value="parallel_fanout">Parallel Fan-Out</option>
              </select>
            </div>
            <p className="text-xs text-gray-500">
              Connect multiple output edges to route based on conditions.
            </p>
          </>
        )}

        {/* Evaluator Node Config */}
        {nodeType === "evaluator" && (
          <>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Evaluation Mode</label>
              <select
                value={(config.evaluation_mode as string) || "schema_only"}
                onChange={(e) => updateField("evaluation_mode", e.target.value)}
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="schema_only">Schema Validation</option>
                <option value="llm_judge">LLM-as-Judge</option>
                <option value="custom_function">Custom Function</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Passing Threshold: {(config.passing_threshold as number) ?? 0.7}
              </label>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={(config.passing_threshold as number) ?? 0.7}
                onChange={(e) => updateField("passing_threshold", parseFloat(e.target.value))}
                className="w-full"
              />
            </div>
          </>
        )}

        {/* HITL Node Config */}
        {nodeType === "hitl" && (
          <>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Approval Mode</label>
              <select
                value={(config.approval_mode as string) || "approve_reject"}
                onChange={(e) => updateField("approval_mode", e.target.value)}
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="approve_reject">Approve / Reject</option>
                <option value="provide_input">Provide Input</option>
                <option value="edit_output">Edit Output</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Timeout (hours)</label>
              <input
                type="number"
                min={1}
                value={(config.timeout_hours as number) || 24}
                onChange={(e) => updateField("timeout_hours", parseInt(e.target.value))}
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </>
        )}

        {/* Input/Output — minimal config */}
        {(nodeType === "input" || nodeType === "output") && (
          <p className="text-xs text-gray-500">
            {nodeType === "input"
              ? "This node defines the workflow's input interface. Data flows to connected downstream nodes."
              : "This node collects outputs from upstream nodes as the workflow's final result."}
          </p>
        )}

        {/* Node ID (read-only) */}
        <div className="pt-2 border-t">
          <p className="text-xs text-gray-400">
            ID: <code>{node.id}</code>
          </p>
        </div>
      </div>
    </div>
  );
}
