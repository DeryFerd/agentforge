/** Custom node component for AgentForge DAG editor. */

"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import {
  Bot,
  Wrench,
  GitBranch,
  CheckCircle,
  UserCheck,
  LogIn,
  LogOut,
} from "lucide-react";
import clsx from "clsx";

const iconMap: Record<string, React.ElementType> = {
  agent: Bot,
  tool: Wrench,
  router: GitBranch,
  evaluator: CheckCircle,
  hitl: UserCheck,
  input: LogIn,
  output: LogOut,
};

export default function AgentForgeNode({ data, selected }: NodeProps) {
  const Icon = iconMap[(data.nodeType as string) || "agent"] || Bot;
  const color = (data.color as string) || "#3B82F6";
  const label = (data.label as string) || "Node";
  const nodeType = (data.nodeType as string) || "agent";

  return (
    <div
      className={clsx(
        "rounded-lg border-2 bg-white dark:bg-gray-900 shadow-md transition-all min-w-[180px]",
        selected ? "shadow-lg ring-2 ring-blue-400" : "hover:shadow-lg"
      )}
      style={{ borderColor: color }}
    >
      {/* Input handle — left side */}
      {nodeType !== "input" && (
        <Handle
          type="target"
          position={Position.Left}
          className="!w-3 !h-3 !bg-gray-400 dark:!bg-gray-500 !border-2 !border-white dark:!border-gray-900"
        />
      )}

      {/* Node header */}
      <div
        className="flex items-center gap-2 px-3 py-2 rounded-t-md dark:bg-opacity-20"
        style={{ backgroundColor: `${color}15` }}
      >
        <Icon size={16} style={{ color }} />
        <span className="text-xs font-medium uppercase tracking-wide" style={{ color }}>
          {nodeType}
        </span>
      </div>

      {/* Node body */}
      <div className="px-3 py-2">
        <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{label}</p>
      </div>

      {/* Output handle — right side */}
      {nodeType !== "output" && (
        <Handle
          type="source"
          position={Position.Right}
          className="!w-3 !h-3 !bg-gray-400 dark:!bg-gray-500 !border-2 !border-white dark:!border-gray-900"
        />
      )}
    </div>
  );
}
