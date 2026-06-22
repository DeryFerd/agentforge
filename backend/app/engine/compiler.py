"""Workflow Compiler — transforms DAG JSON into a LangGraph StateGraph."""

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph


class NodeResult(TypedDict, total=False):
    """Result from a single node execution."""
    output: dict[str, Any]
    tokens_in: int
    tokens_out: int
    cost_usd: float
    error: str | None


class WorkflowState(TypedDict, total=False):
    """Global state that flows through the entire workflow execution."""
    run_id: str
    workflow_id: str
    status: str  # running | paused | completed | failed
    input_data: dict[str, Any]
    node_results: dict[str, NodeResult]
    global_context: dict[str, Any]
    total_tokens_in: int
    total_tokens_out: int
    total_cost_usd: float
    error: str | None


class WorkflowCompiler:
    """Compiles a workflow DAG JSON into an executable LangGraph graph."""

    def __init__(self, dag: dict[str, Any], node_executors: dict[str, Any]):
        """
        Args:
            dag: The workflow DAG with 'nodes' and 'edges' arrays.
            node_executors: Map of node_type -> executor callable.
        """
        self.dag = dag
        self.node_executors = node_executors
        self.nodes = {n["id"]: n for n in dag.get("nodes", [])}
        self.edges = dag.get("edges", [])

    def compile(self) -> Any:
        """Build and return a compiled LangGraph StateGraph."""
        graph = StateGraph(WorkflowState)

        # Add each node to the graph
        for node_id, node_data in self.nodes.items():
            node_type = node_data.get("type", "agent")
            executor = self.node_executors.get(node_type)
            if executor is None:
                raise ValueError(f"No executor registered for node type '{node_type}'")

            # Wrap executor to pass node config
            config = node_data.get("config", {})
            graph.add_node(
                node_id,
                self._make_node_fn(node_id, node_type, config, executor),
            )

        # Add edges
        conditional_sources = self._get_conditional_sources()

        for edge in self.edges:
            source = edge["source"]
            target = edge["target"]

            if source in conditional_sources:
                # Handled by conditional routing below
                continue

            # Regular edge
            graph.add_edge(source, target)

        # Add conditional edges for router nodes
        for source_id in conditional_sources:
            source_node = self.nodes[source_id]
            if source_node.get("type") == "router":
                routing_map = self._build_routing_map(source_id)
                graph.add_conditional_edges(
                    source_id,
                    self._make_router_fn(source_id, source_node.get("config", {})),
                    routing_map,
                )

        # Set entry and exit points
        input_nodes = [nid for nid, n in self.nodes.items() if n.get("type") == "input"]
        output_nodes = [nid for nid, n in self.nodes.items() if n.get("type") == "output"]

        if input_nodes:
            graph.set_entry_point(input_nodes[0])
        elif self.nodes:
            # Use first node with no incoming edges
            targets = {e["target"] for e in self.edges}
            roots = [nid for nid in self.nodes if nid not in targets]
            graph.set_entry_point(roots[0] if roots else list(self.nodes.keys())[0])

        if output_nodes:
            graph.add_edge(output_nodes[0], END)

        return graph.compile()

    def _make_node_fn(self, node_id: str, node_type: str, config: dict, executor: Any):
        """Create a node function that wraps the executor with config context."""
        async def node_fn(state: WorkflowState) -> dict:
            # Get upstream results from connected edges
            upstream_outputs = {}
            for edge in self.edges:
                if edge["target"] == node_id:
                    source_result = state.get("node_results", {}).get(edge["source"], {})
                    upstream_outputs[edge["source"]] = source_result.get("output", {})

            # Build execution context
            context = {
                "node_id": node_id,
                "node_type": node_type,
                "config": config,
                "input_data": state.get("input_data", {}),
                "upstream_outputs": upstream_outputs,
                "global_context": state.get("global_context", {}),
            }

            # Execute the node
            result = await executor.execute(context)

            # Update state
            node_results = dict(state.get("node_results", {}))
            node_results[node_id] = result

            return {
                "node_results": node_results,
                "total_tokens_in": state.get("total_tokens_in", 0) + result.get("tokens_in", 0),
                "total_tokens_out": state.get("total_tokens_out", 0) + result.get("tokens_out", 0),
                "total_cost_usd": state.get("total_cost_usd", 0.0) + result.get("cost_usd", 0.0),
            }

        return node_fn

    def _make_router_fn(self, source_id: str, config: dict):
        """Create a routing function for router nodes.
        
        The router executor evaluates conditions and stores the selected route
        in node_results[source_id]["output"]["selected_route"]. This function
        reads that output and routes to the corresponding target node.
        """
        conditions = config.get("conditions", [])
        
        # Build mapping from condition names to target node IDs
        edge_targets = [e["target"] for e in self.edges if e["source"] == source_id]
        
        # Map condition names to targets
        name_to_target = {}
        for condition in conditions:
            name = condition.get("name", "")
            target = condition.get("target", name)
            if name:
                name_to_target[name] = target
        
        def router_fn(state: WorkflowState) -> str:
            # Get the router node's output from state
            node_results = state.get("node_results", {})
            router_output = node_results.get(source_id, {}).get("output", {})
            selected_route = router_output.get("selected_route")
            
            if selected_route:
                # Map the selected route name to a target node ID
                target = name_to_target.get(selected_route, selected_route)
                if target in edge_targets:
                    return target
            
            # Default: first outgoing edge
            if edge_targets:
                return edge_targets[0]
            
            return END

        return router_fn

    def _get_conditional_sources(self) -> set[str]:
        """Find node IDs that need conditional routing (router nodes)."""
        router_nodes = {nid for nid, n in self.nodes.items() if n.get("type") == "router"}
        return router_nodes

    def _build_routing_map(self, source_id: str) -> dict[str, str]:
        """Build a mapping from route names to target node IDs."""
        mapping = {}
        for edge in self.edges:
            if edge["source"] == source_id:
                target = edge["target"]
                mapping[target] = target
        mapping["__end__"] = END
        return mapping
