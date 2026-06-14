/** DAG Editor page — full-screen canvas for building workflows. */

"use client";

import { useEffect, useCallback, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { useWorkflowStore } from "@/stores/workflow-store";
import { Play, Save, CheckCircle, XCircle, AlertTriangle, Trash2, Loader2, Pencil } from "lucide-react";
import { executionApi } from "@/lib/api";

// Load DAGCanvas client-side only (React Flow needs DOM)
const DAGCanvas = dynamic(() => import("@/components/dag/DAGCanvas"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full text-gray-400">
      Loading editor...
    </div>
  ),
});

// Load NodeConfigPanel client-side only
const NodeConfigPanel = dynamic(() => import("@/components/dag/NodeConfigPanel"), {
  ssr: false,
});

export default function EditorPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const urlWorkflowId = searchParams.get("id");

  const {
    workflowId: storeWorkflowId,
    workflowName,
    isDirty,
    isSaving,
    nodes,
    edges,
    validation,
    removeNode,
    selectedNodeId,
    setValidation,
    saveWorkflow,
    loadWorkflow,
    setWorkflowMeta,
    lastSaveMessage,
  } = useWorkflowStore();

  const [isEditingName, setIsEditingName] = useState(false);
  const [nameInput, setNameInput] = useState(workflowName);
  const [runMessage, setRunMessage] = useState<string | null>(null);

  // Load workflow from URL param on mount
  useEffect(() => {
    if (urlWorkflowId) {
      loadWorkflow(urlWorkflowId);
    }
  }, [urlWorkflowId, loadWorkflow]);

  // After first save, update URL with the new workflow ID
  useEffect(() => {
    if (storeWorkflowId && storeWorkflowId !== urlWorkflowId) {
      router.replace(`/editor?id=${storeWorkflowId}`);
    }
  }, [storeWorkflowId, urlWorkflowId, router]);

  // Keep nameInput synced
  useEffect(() => {
    setNameInput(workflowName);
  }, [workflowName]);

  // Save handler
  const handleSave = useCallback(async () => {
    await saveWorkflow();
  }, [saveWorkflow]);

  // Ctrl+S keyboard shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        handleSave();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handleSave]);

  // Validate handler
  const handleValidate = async () => {
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

    const errors: string[] = [];
    const warnings: string[] = [];

    if (nodes.length === 0) errors.push("No nodes defined");
    if (edges.length === 0 && nodes.length > 1) warnings.push("No edges connecting nodes");

    const nodeTypes = nodes.map((n) => n.data?.nodeType);
    if (!nodeTypes.includes("input")) warnings.push("No Input node");
    if (!nodeTypes.includes("output")) warnings.push("No Output node");

    // Check for orphan nodes
    const connectedIds = new Set<string>();
    edges.forEach((e) => {
      connectedIds.add(e.source);
      connectedIds.add(e.target);
    });
    nodes.forEach((n) => {
      if (!connectedIds.has(n.id) && nodes.length > 1) {
        warnings.push(`Node '${n.data?.label || n.id}' is not connected`);
      }
    });

    setValidation({
      valid: errors.length === 0,
      errors,
      warnings,
      node_count: nodes.length,
      edge_count: edges.length,
    });
  };

  // Run handler
  const handleRun = async () => {
    if (!storeWorkflowId) {
      setRunMessage("Save the workflow first before running.");
      return;
    }
    try {
      setRunMessage("Triggering execution...");
      await executionApi.trigger(storeWorkflowId, {});
      setRunMessage("Execution queued! Check the history page for results.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Run failed";
      setRunMessage(`Error: ${msg}`);
    }
    setTimeout(() => setRunMessage(null), 5000);
  };

  // Name editing
  const commitName = () => {
    setIsEditingName(false);
    if (nameInput.trim() && nameInput !== workflowName) {
      setWorkflowMeta(
        storeWorkflowId,
        nameInput.trim(),
        useWorkflowStore.getState().workflowDescription
      );
      useWorkflowStore.getState().setDirty(true);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-white">
      {/* Top bar */}
      <header className="flex items-center justify-between px-4 py-2 border-b bg-white z-20">
        <div className="flex items-center gap-3">
          <a href="/" className="text-sm text-gray-500 hover:text-gray-700">
            ← Back
          </a>

          {isEditingName ? (
            <input
              autoFocus
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              onBlur={commitName}
              onKeyDown={(e) => e.key === "Enter" && commitName()}
              className="text-lg font-semibold text-gray-800 bg-gray-100 rounded px-2 py-0.5 border border-gray-300 outline-none focus:border-blue-500"
            />
          ) : (
            <button
              onClick={() => setIsEditingName(true)}
              className="flex items-center gap-1.5 text-lg font-semibold text-gray-800 hover:text-blue-600 transition-colors"
            >
              {workflowName}
              <Pencil size={12} className="text-gray-400" />
            </button>
          )}

          {isDirty && (
            <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full">
              Unsaved
            </span>
          )}
          {lastSaveMessage && (
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                lastSaveMessage.startsWith("Error")
                  ? "bg-red-100 text-red-700"
                  : "bg-green-100 text-green-700"
              }`}
            >
              {lastSaveMessage}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <a
            href={`/executions${storeWorkflowId ? `?workflow_id=${storeWorkflowId}` : ""}`}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md bg-gray-100 hover:bg-gray-200 text-gray-700 transition-colors"
          >
            History
          </a>
          <button
            onClick={handleValidate}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md bg-gray-100 hover:bg-gray-200 text-gray-700 transition-colors"
          >
            <CheckCircle size={14} />
            Validate
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving || !isDirty}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white transition-colors"
          >
            {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            {isSaving ? "Saving..." : "Save"}
          </button>
          <button
            onClick={handleRun}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md bg-green-600 hover:bg-green-700 text-white transition-colors"
          >
            <Play size={14} />
            Run
          </button>
        </div>
      </header>

      {/* Run message */}
      {runMessage && (
        <div className="px-4 py-2 bg-blue-50 text-blue-700 text-sm border-b">
          {runMessage}
        </div>
      )}

      {/* Canvas + Config Panel */}
      <div className="flex-1 relative flex">
        <div className="flex-1 relative">
          <DAGCanvas />
        </div>
        <NodeConfigPanel />
      </div>

      {/* Validation bar */}
      {validation && (
        <div
          className={`px-4 py-2 border-t text-sm flex items-center gap-2 flex-wrap ${
            validation.valid ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
          }`}
        >
          {validation.valid ? <CheckCircle size={14} /> : <XCircle size={14} />}
          <span>
            {validation.valid ? "Valid" : "Invalid"} — {validation.node_count} nodes, {validation.edge_count} edges
          </span>
          {validation.errors.map((e, i) => (
            <span key={`e-${i}`} className="ml-2 text-red-600">
              • {e}
            </span>
          ))}
          {validation.warnings.map((w, i) => (
            <span key={`w-${i}`} className="ml-2 text-yellow-600 flex items-center gap-1">
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
