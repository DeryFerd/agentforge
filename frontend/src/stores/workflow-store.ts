/** Zustand store for DAG editor state management. */

import { create } from "zustand";
import type { Edge, Node } from "@xyflow/react";
import type { NodeType, ValidationResult } from "@/lib/types";

interface WorkflowState {
  // Workflow metadata
  workflowId: string | null;
  workflowName: string;
  workflowDescription: string;
  isDirty: boolean;

  // DAG state
  nodes: Node[];
  edges: Edge[];

  // UI state
  selectedNodeId: string | null;
  isPanelOpen: boolean;

  // Validation
  validation: ValidationResult | null;

  // Actions
  setWorkflowMeta: (id: string, name: string, description: string) => void;
  setNodes: (nodes: Node[]) => void;
  setEdges: (edges: Edge[]) => void;
  addNode: (type: NodeType, position: { x: number; y: number }) => void;
  removeNode: (nodeId: string) => void;
  updateNodeData: (nodeId: string, data: Record<string, unknown>) => void;
  selectNode: (nodeId: string | null) => void;
  setValidation: (validation: ValidationResult | null) => void;
  setDirty: (dirty: boolean) => void;
  reset: () => void;
}

let nodeCounter = 0;

const defaultNodeConfigs: Record<NodeType, Record<string, unknown>> = {
  agent: { system_prompt: "", model: { provider: "openai", model_id: "gpt-4o-mini", temperature: 0.3 }, tools: [] },
  tool: { tool: { server: "", tool: "" }, input_mapping: {}, output_mapping: {} },
  router: { routing_mode: "conditional", conditions: [] },
  evaluator: { evaluation_mode: "schema_only", criteria: [], passing_threshold: 0.7 },
  hitl: { approval_mode: "approve_reject", timeout_hours: 24 },
  input: {},
  output: {},
};

const nodeColors: Record<NodeType, string> = {
  agent: "#3B82F6",
  tool: "#8B5CF6",
  router: "#F59E0B",
  evaluator: "#10B981",
  hitl: "#EC4899",
  input: "#6B7280",
  output: "#6B7280",
};

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  workflowId: null,
  workflowName: "Untitled Workflow",
  workflowDescription: "",
  isDirty: false,
  nodes: [],
  edges: [],
  selectedNodeId: null,
  isPanelOpen: false,
  validation: null,

  setWorkflowMeta: (id, name, description) =>
    set({ workflowId: id, workflowName: name, workflowDescription: description }),

  setNodes: (nodes) => set({ nodes, isDirty: true }),
  setEdges: (edges) => set({ edges, isDirty: true }),

  addNode: (type, position) => {
    nodeCounter += 1;
    const id = `${type}_${Date.now()}_${nodeCounter}`;
    const newNode: Node = {
      id,
      type: "agentForgeNode",
      position,
      data: {
        label: `${type.charAt(0).toUpperCase() + type.slice(1)} ${nodeCounter}`,
        nodeType: type,
        color: nodeColors[type],
        config: defaultNodeConfigs[type],
      },
    };
    set((state) => ({
      nodes: [...state.nodes, newNode],
      isDirty: true,
    }));
  },

  removeNode: (nodeId) =>
    set((state) => ({
      nodes: state.nodes.filter((n) => n.id !== nodeId),
      edges: state.edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
      selectedNodeId: state.selectedNodeId === nodeId ? null : state.selectedNodeId,
      isDirty: true,
    })),

  updateNodeData: (nodeId, data) =>
    set((state) => ({
      nodes: state.nodes.map((n) =>
        n.id === nodeId ? { ...n, data: { ...n.data, ...data } } : n
      ),
      isDirty: true,
    })),

  selectNode: (nodeId) => set({ selectedNodeId: nodeId, isPanelOpen: nodeId !== null }),

  setValidation: (validation) => set({ validation }),

  setDirty: (dirty) => set({ isDirty: dirty }),

  reset: () =>
    set({
      workflowId: null,
      workflowName: "Untitled Workflow",
      workflowDescription: "",
      isDirty: false,
      nodes: [],
      edges: [],
      selectedNodeId: null,
      isPanelOpen: false,
      validation: null,
    }),
}));
