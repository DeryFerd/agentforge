/** Workflow version history panel — view and restore past versions. */

"use client";

import { useState, useEffect } from "react";
import { Clock, RotateCcw, GitBranch, ChevronDown, ChevronRight } from "lucide-react";
import api from "@/lib/api";

interface WorkflowVersion {
  id: string;
  version_number: number;
  dag_json: Record<string, unknown>;
  created_at: string;
}

interface Props {
  workflowId: string | null;
  onRestore?: (dag: Record<string, unknown>) => void;
}

export default function VersionHistory({ workflowId, onRestore }: Props) {
  const [versions, setVersions] = useState<WorkflowVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (!workflowId || !expanded) return;
    fetchVersions();
  }, [workflowId, expanded]);

  const fetchVersions = async () => {
    if (!workflowId) return;
    setLoading(true);
    try {
      // The versions endpoint would be GET /workflows/{id}/versions
      // For now, we derive versions from the workflow's version number
      const response = await api.get(`/workflows/${workflowId}`);
      const wf = response.data;
      // Create a pseudo-version list from the current workflow
      const versionList: WorkflowVersion[] = [];
      for (let v = wf.version; v >= 1; v--) {
        versionList.push({
          id: `${workflowId}-v${v}`,
          version_number: v,
          dag_json: v === wf.version ? wf.dag_json : {},
          created_at: v === wf.version ? wf.updated_at : wf.created_at,
        });
      }
      setVersions(versionList);
    } catch {
      console.error("Failed to fetch versions");
    } finally {
      setLoading(false);
    }
  };

  const handleRestore = (version: WorkflowVersion) => {
    if (Object.keys(version.dag_json).length === 0) {
      alert("Version data not available for this version. Only the current version's data is stored.");
      return;
    }
    if (confirm(`Restore version ${version.version_number}? This will overwrite the current workflow.`)) {
      onRestore?.(version.dag_json);
    }
  };

  return (
    <div className="border-t dark:border-gray-700 bg-white dark:bg-gray-900">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
      >
        <span className="flex items-center gap-2">
          <GitBranch size={14} />
          Version History
        </span>
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>

      {expanded && (
        <div className="px-4 pb-3">
          {loading ? (
            <p className="text-xs text-gray-400 dark:text-gray-500 py-2">Loading versions...</p>
          ) : versions.length === 0 ? (
            <p className="text-xs text-gray-400 dark:text-gray-500 py-2">No version history available.</p>
          ) : (
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {versions.map((v) => (
                <div
                  key={v.id}
                  className="flex items-center justify-between px-3 py-2 rounded bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Clock size={12} className="text-gray-400 dark:text-gray-500" />
                    <span className="text-xs font-medium text-gray-700 dark:text-gray-300">v{v.version_number}</span>
                    <span className="text-xs text-gray-400 dark:text-gray-500">
                      {new Date(v.created_at).toLocaleString()}
                    </span>
                  </div>
                  {v.version_number !== versions[0]?.version_number && (
                    <button
                      onClick={() => handleRestore(v)}
                      className="flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
                    >
                      <RotateCcw size={10} /> Restore
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
