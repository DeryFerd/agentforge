"""Workflow DAG validation engine — cycle detection, orphan nodes, type checking."""

from typing import Any


class DAGValidator:
    """Validates a workflow DAG JSON structure."""

    VALID_NODE_TYPES = {"agent", "tool", "router", "evaluator", "hitl", "input", "output"}

    def __init__(self, dag: dict[str, Any]):
        self.dag = dag
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate(self) -> dict[str, Any]:
        """Run all validation checks and return results."""
        self.errors = []
        self.warnings = []

        self._check_structure()
        if self.errors:
            return self._result()

        self._check_node_types()
        self._check_required_nodes()
        self._check_edges()
        self._check_cycles()
        self._check_orphan_nodes()
        self._check_node_configs()

        return self._result()

    def _result(self) -> dict[str, Any]:
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "node_count": len(self.dag.get("nodes", [])),
            "edge_count": len(self.dag.get("edges", [])),
        }

    def _check_structure(self) -> None:
        if not isinstance(self.dag, dict):
            self.errors.append("DAG must be a JSON object")
            return
        if "nodes" not in self.dag:
            self.errors.append("DAG must have a 'nodes' array")
        elif not isinstance(self.dag["nodes"], list):
            self.errors.append("'nodes' must be an array")
        if "edges" not in self.dag:
            self.errors.append("DAG must have an 'edges' array")
        elif not isinstance(self.dag["edges"], list):
            self.errors.append("'edges' must be an array")

    def _check_node_types(self) -> None:
        for node in self.dag.get("nodes", []):
            node_type = node.get("type")
            if not node_type:
                self.errors.append(f"Node '{node.get('id', '?')}' missing 'type' field")
            elif node_type not in self.VALID_NODE_TYPES:
                self.errors.append(
                    f"Node '{node.get('id', '?')}' has invalid type '{node_type}'. "
                    f"Valid types: {', '.join(sorted(self.VALID_NODE_TYPES))}"
                )

    def _check_required_nodes(self) -> None:
        node_types = [n.get("type") for n in self.dag.get("nodes", [])]
        if "input" not in node_types:
            self.warnings.append("No Input node found — workflow won't have defined inputs")
        if "output" not in node_types:
            self.warnings.append("No Output node found — workflow won't produce structured output")

    def _check_edges(self) -> None:
        node_ids = {n.get("id") for n in self.dag.get("nodes", [])}
        for i, edge in enumerate(self.dag.get("edges", [])):
            source = edge.get("source")
            target = edge.get("target")
            if not source:
                self.errors.append(f"Edge {i}: missing 'source'")
            elif source not in node_ids:
                self.errors.append(f"Edge {i}: source '{source}' does not match any node")
            if not target:
                self.errors.append(f"Edge {i}: missing 'target'")
            elif target not in node_ids:
                self.errors.append(f"Edge {i}: target '{target}' does not match any node")

    def _check_cycles(self) -> None:
        """Detect cycles using Kahn's algorithm (topological sort)."""
        nodes = self.dag.get("nodes", [])
        edges = self.dag.get("edges", [])

        if not nodes:
            return

        # Build adjacency list and in-degree count
        adj: dict[str, list[str]] = {n["id"]: [] for n in nodes}
        in_degree: dict[str, int] = {n["id"]: 0 for n in nodes}

        for edge in edges:
            src, tgt = edge.get("source"), edge.get("target")
            if src in adj and tgt in in_degree:
                adj[src].append(tgt)
                in_degree[tgt] += 1

        # Kahn's algorithm
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        visited = 0

        while queue:
            current = queue.pop(0)
            visited += 1
            for neighbor in adj.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited < len(nodes):
            self.errors.append(
                "Cycle detected in workflow DAG — workflows must be directed acyclic graphs"
            )

    def _check_orphan_nodes(self) -> None:
        """Find nodes with no incoming or outgoing edges."""
        if len(self.dag.get("nodes", [])) <= 1:
            return

        connected = set()
        for edge in self.dag.get("edges", []):
            connected.add(edge.get("source"))
            connected.add(edge.get("target"))

        for node in self.dag.get("nodes", []):
            nid = node.get("id")
            if nid and nid not in connected:
                self.warnings.append(f"Node '{nid}' ({node.get('type', '?')}) is not connected to any edge")

    def _check_node_configs(self) -> None:
        """Check that nodes have required configuration fields."""
        for node in self.dag.get("nodes", []):
            nid = node.get("id", "?")
            ntype = node.get("type")
            config = node.get("config", {})

            if ntype == "agent":
                if not config.get("system_prompt"):
                    self.warnings.append(f"Agent node '{nid}' has no system prompt")
                if not config.get("model"):
                    self.warnings.append(f"Agent node '{nid}' has no model configured")

            if ntype == "tool":
                if not config.get("tool"):
                    self.warnings.append(f"Tool node '{nid}' has no tool binding")

            if ntype == "router":
                conditions = config.get("conditions", [])
                if not conditions:
                    self.warnings.append(f"Router node '{nid}' has no routing conditions")
