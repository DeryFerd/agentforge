/** Main DAG editor canvas using React Flow. */

"use client";

import { useCallback, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  type Connection,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import AgentForgeNode from "./AgentForgeNode";
import NodeToolbar from "./NodeToolbar";
import { useWorkflowStore } from "@/stores/workflow-store";

export default function DAGCanvas() {
  const storeNodes = useWorkflowStore((s) => s.nodes);
  const storeEdges = useWorkflowStore((s) => s.edges);
  const setStoreNodes = useWorkflowStore((s) => s.setNodes);
  const setStoreEdges = useWorkflowStore((s) => s.setEdges);
  const selectNode = useWorkflowStore((s) => s.selectNode);

  const [nodes, setNodes, onNodesChange] = useNodesState(storeNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(storeEdges);

  // Custom node types
  const nodeTypesMap = useMemo(
    () => ({ agentForgeNode: AgentForgeNode }),
    []
  );

  // Handle new connections (edges)
  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge({ ...connection, animated: true }, eds));
      // Sync back to store
      const newEdges = addEdge({ ...connection, animated: true }, edges);
      setStoreEdges(newEdges as Edge[]);
    },
    [edges, setEdges, setStoreEdges]
  );

  // Sync nodes to store on change
  const handleNodesChange: typeof onNodesChange = useCallback(
    (changes) => {
      onNodesChange(changes);
      // Small delay to let React Flow process changes
      setTimeout(() => {
        setStoreNodes(nodes);
      }, 0);
    },
    [nodes, onNodesChange, setStoreNodes]
  );

  // Handle node click for selection
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: { id: string }) => {
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
        onNodesChange={handleNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypesMap}
        fitView
        snapToGrid
        snapGrid={[15, 15]}
        deleteKeyCode="Delete"
        className="bg-gray-50"
      >
        <Background gap={15} size={1} color="#e5e7eb" />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={(n) => (n.data?.color as string) || "#6B7280"}
          maskColor="rgba(0,0,0,0.08)"
          className="!bg-white !border !border-gray-200 !rounded-lg"
        />
      </ReactFlow>
      <NodeToolbar />
    </div>
  );
}
