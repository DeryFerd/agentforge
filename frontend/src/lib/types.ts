/** TypeScript types for AgentForge frontend. */

export interface User {
  id: string;
  email: string;
  full_name: string;
}

export interface Workspace {
  id: string;
  name: string;
  owner_id: string;
}

export interface Workflow {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  version: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DAGNode {
  id: string;
  type: NodeType;
  position: { x: number; y: number };
  data: NodeConfig;
}

export interface DAGEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
}

export type NodeType = "agent" | "tool" | "router" | "evaluator" | "hitl" | "input" | "output";

export interface NodeConfig {
  label: string;
  type: NodeType;
  config: Record<string, unknown>;
}

export interface AgentNodeConfig extends NodeConfig {
  type: "agent";
  config: {
    system_prompt: string;
    model?: { provider: string; model_id: string; temperature?: number };
    tools?: Array<{ server: string; tool: string }>;
    output_schema?: Record<string, unknown>;
    timeout_seconds?: number;
  };
}

export interface ToolNodeConfig extends NodeConfig {
  type: "tool";
  config: {
    tool: { server: string; tool: string };
    input_mapping?: Record<string, string>;
    output_mapping?: Record<string, string>;
  };
}

export interface RouterNodeConfig extends NodeConfig {
  type: "router";
  config: {
    routing_mode: "conditional" | "llm_based" | "parallel_fanout";
    conditions?: Array<{ name: string; expression: string; target: string }>;
  };
}

export interface Execution {
  id: string;
  workflow_id: string;
  status: "queued" | "running" | "paused" | "completed" | "failed" | "cancelled";
  trigger_type: string;
  total_cost_usd: number;
  created_at: string;
  completed_at: string | null;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  node_count: number;
  edge_count: number;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}
