/** DAG Editor page — full-screen canvas for building workflows. */

"use client";

import dynamic from "next/dynamic";
import { useWorkflowStore } from "@/stores/workflow-store";
import { Play, Save, CheckCircle, XCircle, AlertTriangle, Trash2 } from "lucide-react";

// Load DAGCanvas client-side only (React Flow needs DOM)
const DAGCanvas = dynamic(() => import("@/components/dag/DAGCanvas"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full text-gray-400">
      Loading editor...
    </div>
  ),
});

export default function EditorPage() {
  const { workflowName, isDirty, nodes, edges, validation, removeNode, selectedNodeId, setValidation } =
    useWorkflowStore();

  const handleValidate = async () => {
    // Build DAG JSON from current canvas state
    const dag = {
      nodes: nodes.map((n) => ({
        id: n.id,
        type: n.data?.nodeType || "agent",
        config: n.data?.config || {},
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
      })),
    };

    // Simple client-side validation for now; backend validation in production
    const errors: string[] = [];
    const warnings: string[] = [];

    if (nodes.length === 0) errors.push("No nodes defined");
    if (edges.length === 0 && nodes.length > 1) warnings.push("No edges connecting nodes");

    const nodeTypes = nodes.map((n) => n.data?.nodeType);
    if (!nodeTypes.includes("input")) warnings.push("No Input node");
    if (!nodeTypes.includes("output")) warnings.push("No Output node");

    setValidation({
      valid: errors.length === 0,
      errors,
      warnings,
      node_count: nodes.length,
      edge_count: edges.length,
    });
  };

  return (
    <div className="h-screen flex flex-col bg-white">
      {/* Top bar */}
      <header className="flex items-center justify-between px-4 py-2 border-b bg-white z-20">
        <div className="flex items-center gap-3">
          <a href="/" className="text-sm text-gray-500 hover:text-gray-700">
            ← Back
          </a>
          <h1 className="text-lg font-semibold text-gray-800">{workflowName}</h1>
          {isDirty && (
            <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full">
              Unsaved
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleValidate}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md bg-gray-100 hover:bg-gray-200 text-gray-700 transition-colors"
          >
            <CheckCircle size={14} />
            Validate
          </button>
          <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md bg-blue-600 hover:bg-blue-700 text-white transition-colors">
            <Save size={14} />
            Save
          </button>
          <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md bg-green-600 hover:bg-green-700 text-white transition-colors">
            <Play size={14} />
            Run
          </button>
        </div>
      </header>

      {/* Canvas */}
      <div className="flex-1 relative">
        <DAGCanvas />
      </div>

      {/* Validation bar */}
      {validation && (
        <div
          className={`px-4 py-2 border-t text-sm flex items-center gap-2 ${
            validation.valid ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
          }`}
        >
          {validation.valid ? <CheckCircle size={14} /> : <XCircle size={14} />}
          <span>
            {validation.valid ? "Valid" : "Invalid"} — {validation.node_count} nodes, {validation.edge_count} edges
          </span>
          {validation.errors.map((e, i) => (
            <span key={i} className="ml-2 text-red-600">
              • {e}
            </span>
          ))}
          {validation.warnings.map((w, i) => (
            <span key={i} className="ml-2 text-yellow-600 flex items-center gap-1">
              <AlertTriangle size={12} /> {w}
            </span>
          ))}
        </div>
      )}

      {/* Delete selected node button */}
      {selectedNodeId && (
        <div className="absolute bottom-16 right-4 z-20">
          <button
            onClick={() => removeNode(selectedNodeId)}
            className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg bg-red-600 hover:bg-red-700 text-white shadow-lg transition-colors"
          >
            <Trash2 size={14} />
            Delete Node
          </button>
        </div>
      )}
    </div>
  );
}
