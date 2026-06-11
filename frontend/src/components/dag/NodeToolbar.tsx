/** Toolbar for adding nodes to the DAG canvas. */

"use client";

import {
  Bot,
  Wrench,
  GitBranch,
  CheckCircle,
  UserCheck,
  LogIn,
  LogOut,
} from "lucide-react";
import { useWorkflowStore } from "@/stores/workflow-store";
import type { NodeType } from "@/lib/types";

const nodeTypes: Array<{ type: NodeType; label: string; icon: React.ElementType; color: string }> = [
  { type: "agent", label: "Agent", icon: Bot, color: "#3B82F6" },
  { type: "tool", label: "Tool", icon: Wrench, color: "#8B5CF6" },
  { type: "router", label: "Router", icon: GitBranch, color: "#F59E0B" },
  { type: "evaluator", label: "Evaluator", icon: CheckCircle, color: "#10B981" },
  { type: "hitl", label: "Human Review", icon: UserCheck, color: "#EC4899" },
  { type: "input", label: "Input", icon: LogIn, color: "#6B7280" },
  { type: "output", label: "Output", icon: LogOut, color: "#6B7280" },
];

export default function NodeToolbar() {
  const addNode = useWorkflowStore((s) => s.addNode);

  const handleAdd = (type: NodeType) => {
    // Place nodes at a semi-random position in the viewport
    const x = 250 + Math.random() * 400;
    const y = 100 + Math.random() * 300;
    addNode(type, { x, y });
  };

  return (
    <div className="absolute top-4 left-4 z-10 flex flex-col gap-1 bg-white rounded-lg shadow-lg border p-2">
      <p className="text-xs font-semibold text-gray-500 px-2 py-1 uppercase tracking-wide">
        Add Node
      </p>
      {nodeTypes.map(({ type, label, icon: Icon, color }) => (
        <button
          key={type}
          onClick={() => handleAdd(type)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm text-gray-700 hover:bg-gray-100 transition-colors"
        >
          <Icon size={14} style={{ color }} />
          {label}
        </button>
      ))}
    </div>
  );
}
