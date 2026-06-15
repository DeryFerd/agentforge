/** Main DAG editor canvas using React Flow. */

"use client";

import { useCallback, useEffect, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  type Connection,
  type Edge,
  type Node,
  type OnNodesChange,
  type OnEdgesChange,
  applyNodeChanges,
  applyEdgeChanges,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import AgentForgeNode from "./AgentForgeNode";
import NodeToolbar from "./NodeToolbar";
import { useWorkflowStore } from "@/stores/workflow-store";

export default function DAGCanvas() {
  const nodes = useWorkflowStore((s) => s.nodes);
  const edges = useWorkflowStore((s) => s.edges);
  const setStoreNodes = useWorkflowStore((s) => s.setNodes);
  const setStoreEdges = useWorkflowStore((s) => s.setEdges);
  const selectNode = useWorkflowStore((s) => s.selectNode);

  // Custom node types — memoized to prevent re-renders
  const nodeTypesMap = useMemo(
    () => ({ agentForgeNode: AgentForgeNode }),
    []
  );

  // Handle node changes (drag, select, delete) — apply to Zustand store directly
  // Filter out 'select' and 'dimensions' changes — they should NOT mark the workflow as dirty
  const onNodesChange: OnNodesChange = useCallback(
    (changes) => {
      const updatedNodes = applyNodeChanges(changes, nodes);
      const hasStructuralChange = changes.some(
        (c) => c.type !== "select" && c.type !== "dimensions"
      );
      if (hasStructuralChange) {
        setStoreNodes(updatedNodes);
      } else {
        // Only update nodes array without setting isDirty
        useWorkflowStore.setState({ nodes: updatedNodes });
      }
    },
    [nodes, setStoreNodes]
  );

  // Handle edge changes
  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => {
      const updatedEdges = applyEdgeChanges(changes, edges);
      const hasStructuralChange = changes.some((c) => c.type !== "select");
      if (hasStructuralChange) {
        setStoreEdges(updatedEdges);
      } else {
        useWorkflowStore.setState({ edges: updatedEdges });
      }
    },
    [edges, setStoreEdges]
  );

  // Handle new connections (edges between nodes)
  const onConnect = useCallback(
    (connection: Connection) => {
      const newEdges = addEdge({ ...connection, animated: true }, edges);
      setStoreEdges(newEdges as Edge[]);
    },
    [edges, setStoreEdges]
  );

  // Handle node click for selection
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      selectNode(node.id);
    },
    [selectNode]
  );

  // Handle pane click to deselect
  const onPaneClick = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  return (
    <div className="w-full h-full relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypesMap}
        fitView
        snapToGrid
        snapGrid={[15, 15]}
        deleteKeyCode="Delete"
        className="bg-gray-50 dark:bg-gray-950"
      >
        <Background gap={15} size={1} color="#e5e7eb" />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={(n) => (n.data?.color as string) || "#6B7280"}
          maskColor="rgba(0,0,0,0.08)"
          className="!bg-white dark:!bg-gray-800 !border !border-gray-200 dark:!border-gray-700 !rounded-lg"
        />
      </ReactFlow>
      <NodeToolbar />
    </div>
  );
}
