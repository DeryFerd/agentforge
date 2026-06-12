"""Unit tests for DAGValidator — cycle detection, orphan nodes, type validation, config checks."""

import pytest

from app.engine.validator import DAGValidator


class TestStructureValidation:
    """Test basic DAG structure checks."""

    def test_empty_dag(self):
        validator = DAGValidator({})
        result = validator.validate()
        assert not result["valid"]
        assert any("nodes" in e for e in result["errors"])
        assert any("edges" in e for e in result["errors"])

    def test_missing_edges(self):
        validator = DAGValidator({"nodes": []})
        result = validator.validate()
        assert not result["valid"]
        assert any("edges" in e for e in result["errors"])

    def test_valid_empty_graph(self):
        validator = DAGValidator({"nodes": [], "edges": []})
        result = validator.validate()
        assert result["valid"]
        assert result["node_count"] == 0

    def test_not_a_dict(self):
        validator = DAGValidator("not a dict")
        result = validator.validate()
        assert not result["valid"]


class TestNodeTypes:
    """Test node type validation."""

    def test_valid_node_types(self):
        dag = {
            "nodes": [
                {"id": "n1", "type": "agent", "config": {}},
                {"id": "n2", "type": "tool", "config": {}},
                {"id": "n3", "type": "router", "config": {}},
                {"id": "n4", "type": "evaluator", "config": {}},
                {"id": "n5", "type": "hitl", "config": {}},
                {"id": "n6", "type": "input", "config": {}},
                {"id": "n7", "type": "output", "config": {}},
            ],
            "edges": [],
        }
        validator = DAGValidator(dag)
        result = validator.validate()
        assert result["valid"]
        assert result["node_count"] == 7

    def test_invalid_node_type(self):
        dag = {
            "nodes": [{"id": "n1", "type": "unknown_type", "config": {}}],
            "edges": [],
        }
        validator = DAGValidator(dag)
        result = validator.validate()
        assert not result["valid"]
        assert any("invalid type" in e for e in result["errors"])

    def test_missing_node_type(self):
        dag = {
            "nodes": [{"id": "n1", "config": {}}],
            "edges": [],
        }
        validator = DAGValidator(dag)
        result = validator.validate()
        assert not result["valid"]
        assert any("missing 'type'" in e for e in result["errors"])


class TestCycleDetection:
    """Test Kahn's algorithm cycle detection."""

    def test_no_cycle_linear(self):
        dag = {
            "nodes": [
                {"id": "a", "type": "input"},
                {"id": "b", "type": "agent"},
                {"id": "c", "type": "output"},
            ],
            "edges": [
                {"source": "a", "target": "b"},
                {"source": "b", "target": "c"},
            ],
        }
        validator = DAGValidator(dag)
        result = validator.validate()
        assert result["valid"]
        assert not any("Cycle" in e for e in result["errors"])

    def test_simple_cycle(self):
        dag = {
            "nodes": [
                {"id": "a", "type": "agent"},
                {"id": "b", "type": "agent"},
            ],
            "edges": [
                {"source": "a", "target": "b"},
                {"source": "b", "target": "a"},
            ],
        }
        validator = DAGValidator(dag)
        result = validator.validate()
        assert not result["valid"]
        assert any("Cycle" in e for e in result["errors"])

    def test_three_node_cycle(self):
        dag = {
            "nodes": [
                {"id": "a", "type": "agent"},
                {"id": "b", "type": "agent"},
                {"id": "c", "type": "agent"},
            ],
            "edges": [
                {"source": "a", "target": "b"},
                {"source": "b", "target": "c"},
                {"source": "c", "target": "a"},
            ],
        }
        validator = DAGValidator(dag)
        result = validator.validate()
        assert not result["valid"]
        assert any("Cycle" in e for e in result["errors"])

    def test_diamond_no_cycle(self):
        """Diamond pattern (fan-out + fan-in) should NOT be a cycle."""
        dag = {
            "nodes": [
                {"id": "a", "type": "input"},
                {"id": "b", "type": "agent"},
                {"id": "c", "type": "agent"},
                {"id": "d", "type": "output"},
            ],
            "edges": [
                {"source": "a", "target": "b"},
                {"source": "a", "target": "c"},
                {"source": "b", "target": "d"},
                {"source": "c", "target": "d"},
            ],
        }
        validator = DAGValidator(dag)
        result = validator.validate()
        assert result["valid"]


class TestEdgeValidation:
    """Test edge reference validation."""

    def test_invalid_source(self):
        dag = {
            "nodes": [{"id": "a", "type": "agent"}],
            "edges": [{"source": "nonexistent", "target": "a"}],
        }
        validator = DAGValidator(dag)
        result = validator.validate()
        assert not result["valid"]
        assert any("nonexistent" in e for e in result["errors"])

    def test_invalid_target(self):
        dag = {
            "nodes": [{"id": "a", "type": "agent"}],
            "edges": [{"source": "a", "target": "nonexistent"}],
        }
        validator = DAGValidator(dag)
        result = validator.validate()
        assert not result["valid"]
        assert any("nonexistent" in e for e in result["errors"])

    def test_missing_source_field(self):
        dag = {
            "nodes": [{"id": "a", "type": "agent"}],
            "edges": [{"target": "a"}],
        }
        validator = DAGValidator(dag)
        result = validator.validate()
        assert not result["valid"]
        assert any("missing 'source'" in e for e in result["errors"])


class TestOrphanNodes:
    """Test orphan node detection."""

    def test_single_node_no_warning(self):
        """A single node with no edges shouldn't warn about orphans."""
        dag = {
            "nodes": [{"id": "a", "type": "agent"}],
            "edges": [],
        }
        validator = DAGValidator(dag)
        result = validator.validate()
        assert result["valid"]
        assert not any("not connected" in w for w in result["warnings"])

    def test_orphan_node_warning(self):
        dag = {
            "nodes": [
                {"id": "a", "type": "agent"},
                {"id": "b", "type": "agent"},
                {"id": "orphan", "type": "agent"},
            ],
            "edges": [{"source": "a", "target": "b"}],
        }
        validator = DAGValidator(dag)
        result = validator.validate()
        assert result["valid"]  # Warnings don't invalidate
        assert any("orphan" in w for w in result["warnings"])


class TestRequiredNodes:
    """Test warnings for missing input/output nodes."""

    def test_warns_no_input(self):
        dag = {
            "nodes": [{"id": "a", "type": "agent"}],
            "edges": [],
        }
        validator = DAGValidator(dag)
        result = validator.validate()
        assert any("Input" in w for w in result["warnings"])

    def test_warns_no_output(self):
        dag = {
            "nodes": [{"id": "a", "type": "agent"}],
            "edges": [],
        }
        validator = DAGValidator(dag)
        result = validator.validate()
        assert any("Output" in w for w in result["warnings"])

    def test_no_warnings_with_both(self):
        dag = {
            "nodes": [
                {"id": "i", "type": "input"},
                {"id": "o", "type": "output"},
            ],
            "edges": [{"source": "i", "target": "o"}],
        }
        validator = DAGValidator(dag)
        result = validator.validate()
        assert not any("Input" in w or "Output" in w for w in result["warnings"])


class TestNodeConfigChecks:
    """Test node configuration validation warnings."""

    def test_agent_no_prompt_warning(self):
        dag = {
            "nodes": [{"id": "a", "type": "agent", "config": {}}],
            "edges": [],
        }
        validator = DAGValidator(dag)
        result = validator.validate()
        assert any("system prompt" in w for w in result["warnings"])

    def test_agent_no_model_warning(self):
        dag = {
            "nodes": [{"id": "a", "type": "agent", "config": {"system_prompt": "test"}}],
            "edges": [],
        }
        validator = DAGValidator(dag)
        result = validator.validate()
        assert any("model" in w for w in result["warnings"])

    def test_tool_no_binding_warning(self):
        dag = {
            "nodes": [{"id": "t", "type": "tool", "config": {}}],
            "edges": [],
        }
        validator = DAGValidator(dag)
        result = validator.validate()
        assert any("tool" in w.lower() for w in result["warnings"])


class TestResultStructure:
    """Test the result dict structure."""

    def test_result_has_required_keys(self):
        validator = DAGValidator({"nodes": [], "edges": []})
        result = validator.validate()
        assert "valid" in result
        assert "errors" in result
        assert "warnings" in result
        assert "node_count" in result
        assert "edge_count" in result

    def test_counts_are_correct(self):
        dag = {
            "nodes": [
                {"id": "a", "type": "agent"},
                {"id": "b", "type": "tool"},
            ],
            "edges": [{"source": "a", "target": "b"}],
        }
        validator = DAGValidator(dag)
        result = validator.validate()
        assert result["node_count"] == 2
        assert result["edge_count"] == 1
