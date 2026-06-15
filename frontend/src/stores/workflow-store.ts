/** Zustand store for DAG editor state management. */

import { create } from "zustand";
import type { Edge, Node } from "@xyflow/react";
import type { NodeType, ValidationResult } from "@/lib/types";
import { workflowApi } from "@/lib/api";

interface WorkflowState {
  // Workflow metadata
  workflowId: string | null;
  workspaceId: string | null;
  workflowName: string;
  workflowDescription: string;
  isDirty: boolean;
  isSaving: boolean;

  // DAG state
  nodes: Node[];
  edges: Edge[];

  // UI state
  selectedNodeId: string | null;
  isPanelOpen: boolean;

  // Validation
  validation: ValidationResult | null;

  // Save status message
  lastSaveMessage: string | null;

  // Actions
  setWorkflowMeta: (id: string | null, name: string, description: string, workspaceId?: string | null) => void;
  setNodes: (nodes: Node[]) => void;
  setEdges: (edges: Edge[]) => void;
  addNode: (type: NodeType, position: { x: number; y: number }) => void;
  removeNode: (nodeId: string) => void;
  updateNodeData: (nodeId: string, data: Record<string, unknown>) => void;
  selectNode: (nodeId: string | null) => void;
  setValidation: (validation: ValidationResult | null) => void;
  setDirty: (dirty: boolean) => void;
  reset: () => void;

  // API actions
  saveWorkflow: () => Promise<void>;
  loadWorkflow: (id: string) => Promise<void>;
  buildDagJson: () => { nodes: object[]; edges: object[] };
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
  workspaceId: null,
  workflowName: "Untitled Workflow",
  workflowDescription: "",
  isDirty: false,
  isSaving: false,
  nodes: [],
  edges: [],
  selectedNodeId: null,
  isPanelOpen: false,
  validation: null,
  lastSaveMessage: null,

  setWorkflowMeta: (id, name, description, workspaceId) =>
    set({ workflowId: id, workflowName: name, workflowDescription: description, workspaceId: workspaceId ?? null }),

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
      workspaceId: null,
      workflowName: "Untitled Workflow",
      workflowDescription: "",
      isDirty: false,
      isSaving: false,
      nodes: [],
      edges: [],
      selectedNodeId: null,
      isPanelOpen: false,
      validation: null,
      lastSaveMessage: null,
    }),

  // ─── API Actions ────────────────────────────────────────────

  buildDagJson: () => {
    const { nodes, edges } = get();
    return {
      nodes: nodes.map((n) => ({
        id: n.id,
        type: (n.data?.nodeType as string) || "agent",
        position: n.position,
        config: (n.data?.config as object) || {},
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        sourceHandle: e.sourceHandle || null,
        targetHandle: e.targetHandle || null,
      })),
    };
  },

  saveWorkflow: async () => {
    const state = get();
    if (state.isSaving) return;

    set({ isSaving: true, lastSaveMessage: null });

    try {
      const dag = state.buildDagJson();

      if (state.workflowId) {
        // Update existing workflow
        const response = await workflowApi.update(state.workflowId, {
          name: state.workflowName,
          description: state.workflowDescription,
          dag_json: dag,
        });
        set({ isDirty: false, isSaving: false, lastSaveMessage: "Saved!" });
        console.log("Workflow updated:", response.data);
      } else {
        // Create new workflow — resolve workspace ID
        let wsId = state.workspaceId;
        if (!wsId && typeof window !== "undefined") {
          wsId = localStorage.getItem("current_workspace_id");
        }

        // If still no workspace, auto-create one
        if (!wsId) {
          try {
            const { workspaceApi } = await import("@/lib/api");
            const wsResponse = await workspaceApi.create("My Workspace");
            wsId = wsResponse.data.id;
            if (typeof window !== "undefined") {
              localStorage.setItem("current_workspace_id", wsId!);
              localStorage.setItem("current_workspace_name", wsResponse.data.name);
            }
          } catch {
            set({ isSaving: false, lastSaveMessage: "Error: Could not create workspace" });
            return;
          }
        }

        const response = await workflowApi.create({
          workspace_id: wsId!,
          name: state.workflowName,
          description: state.workflowDescription,
          dag_json: dag,
        });
        const created = response.data;
        set({
          workflowId: created.id,
          workspaceId: created.workspace_id,
          isDirty: false,
          isSaving: false,
          lastSaveMessage: "Created!",
        });
        console.log("Workflow created:", created);
      }
    } catch (error: unknown) {
      // Extract meaningful error message from axios or generic error
      let msg = "Save failed";
      if (error && typeof error === "object") {
        const axiosErr = error as { response?: { data?: { detail?: string }; status?: number }; message?: string };
        if (axiosErr.response?.data?.detail) {
          msg = axiosErr.response.data.detail;
        } else if (axiosErr.response?.status) {
          msg = `Server error (${axiosErr.response.status})`;
        } else if (axiosErr.message) {
          msg = axiosErr.message;
        }
      }
      set({ isSaving: false, lastSaveMessage: `Error: ${msg}` });
      console.error("Save failed:", error);
    }
  },

  loadWorkflow: async (id: string) => {
    try {
      const response = await workflowApi.get(id);
      const wf = response.data;
      const dag = (wf as unknown as { dag_json?: { nodes?: object[]; edges?: object[] } }).dag_json;

      // Parse nodes back into React Flow format
      const flowNodes: Node[] = (dag?.nodes || []).map((n: unknown) => {
        const node = n as { id: string; type: string; position?: { x: number; y: number }; config?: object };
        const nodeType = (node.type || "agent") as NodeType;
        return {
          id: node.id,
          type: "agentForgeNode",
          position: node.position || { x: 100, y: 100 },
          data: {
            label: `${nodeType.charAt(0).toUpperCase() + nodeType.slice(1)}`,
            nodeType,
            color: nodeColors[nodeType] || "#6B7280",
            config: node.config || defaultNodeConfigs[nodeType] || {},
          },
        };
      });

      const flowEdges: Edge[] = (dag?.edges || []).map((e: unknown) => {
        const edge = e as { id: string; source: string; target: string };
        return {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          animated: true,
        };
      });

      set({
        workflowId: wf.id,
        workspaceId: wf.workspace_id,
        workflowName: wf.name,
        workflowDescription: wf.description || "",
        nodes: flowNodes,
        edges: flowEdges,
        isDirty: false,
        validation: null,
        lastSaveMessage: null,
      });
    } catch (error) {
      console.error("Failed to load workflow:", error);
      set({ lastSaveMessage: "Failed to load workflow" });
    }
  },
}));
