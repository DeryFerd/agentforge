"""Tests for the execution engine — WorkflowCompiler + node executors.

These tests verify the core value proposition:
1. DAG JSON compiles to a LangGraph StateGraph
2. Each node executor produces correct output
3. State flows correctly between nodes
4. Cost tracking works end-to-end
5. Router uses safeeval (no eval())
6. HITL polls Redis correctly
7. Error recovery works
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engine.compiler import WorkflowCompiler, WorkflowState
from app.engine.executors import (
    AgentNodeExecutor,
    EvaluatorNodeExecutor,
    HITLNodeExecutor,
    InputNodeExecutor,
    OutputNodeExecutor,
    RouterNodeExecutor,
    ToolNodeExecutor,
    get_default_executors,
)
from app.engine.validator import DAGValidator


# ─── Compiler Tests ────────────────────────────────────────────────


class TestWorkflowCompiler:
    """Test DAG JSON → LangGraph StateGraph compilation."""

    def test_compile_simple_linear_graph(self):
        """A→B→C should compile without errors."""
        dag = {
            "nodes": [
                {"id": "input", "type": "input", "config": {}},
                {"id": "agent", "type": "agent", "config": {"system_prompt": "test"}},
                {"id": "output", "type": "output", "config": {}},
            ],
            "edges": [
                {"source": "input", "target": "agent"},
                {"source": "agent", "target": "output"},
            ],
        }
        executors = get_default_executors()
        compiler = WorkflowCompiler(dag, executors)
        graph = compiler.compile()
        assert graph is not None

    def test_compile_branching_graph(self):
        """Diamond pattern: A→B, A→C, B→D, C→D."""
        dag = {
            "nodes": [
                {"id": "input", "type": "input", "config": {}},
                {"id": "b", "type": "agent", "config": {}},
                {"id": "c", "type": "agent", "config": {}},
                {"id": "output", "type": "output", "config": {}},
            ],
            "edges": [
                {"source": "input", "target": "b"},
                {"source": "input", "target": "c"},
                {"source": "b", "target": "output"},
                {"source": "c", "target": "output"},
            ],
        }
        executors = get_default_executors()
        compiler = WorkflowCompiler(dag, executors)
        graph = compiler.compile()
        assert graph is not None

    def test_compile_with_router(self):
        """Graph with router node should compile with conditional edges."""
        dag = {
            "nodes": [
                {"id": "input", "type": "input", "config": {}},
                {"id": "router", "type": "router", "config": {"routing_mode": "conditional", "conditions": []}},
                {"id": "branch_a", "type": "agent", "config": {}},
                {"id": "branch_b", "type": "agent", "config": {}},
                {"id": "output", "type": "output", "config": {}},
            ],
            "edges": [
                {"source": "input", "target": "router"},
                {"source": "router", "target": "branch_a"},
                {"source": "router", "target": "branch_b"},
                {"source": "branch_a", "target": "output"},
                {"source": "branch_b", "target": "output"},
            ],
        }
        executors = get_default_executors()
        compiler = WorkflowCompiler(dag, executors)
        graph = compiler.compile()
        assert graph is not None

    def test_compile_invalid_node_type_raises(self):
        """Unknown node type should raise ValueError."""
        dag = {
            "nodes": [
                {"id": "bad", "type": "nonexistent_type", "config": {}},
            ],
            "edges": [],
        }
        executors = get_default_executors()
        compiler = WorkflowCompiler(dag, executors)
        with pytest.raises(ValueError, match="No executor registered"):
            compiler.compile()


# ─── Node Executor Tests ───────────────────────────────────────────


class TestInputNodeExecutor:
    """Test input node passes data through."""

    @pytest.mark.asyncio
    async def test_passes_input_data(self):
        executor = InputNodeExecutor()
        context = {
            "node_id": "input_1",
            "input_data": {"query": "hello", "user_id": "123"},
        }
        result = await executor.execute(context)
        assert result["output"] == {"query": "hello", "user_id": "123"}
        assert result["tokens_in"] == 0
        assert result["cost_usd"] == 0.0


class TestOutputNodeExecutor:
    """Test output node collects upstream."""

    @pytest.mark.asyncio
    async def test_collects_upstream(self):
        executor = OutputNodeExecutor()
        context = {
            "node_id": "output_1",
            "upstream_outputs": {
                "agent_1": {"response": "Hello world"},
                "agent_2": {"summary": "A greeting"},
            },
        }
        result = await executor.execute(context)
        assert "result" in result["output"]
        assert "agent_1" in result["output"]["result"]


class TestAgentNodeExecutor:
    """Test agent node with mocked LLM calls."""

    @pytest.mark.asyncio
    async def test_echo_fallback_when_no_api_key(self):
        """When no API key configured, should return echo response."""
        executor = AgentNodeExecutor()
        context = {
            "node_id": "agent_1",
            "config": {
                "system_prompt": "You are a test assistant.",
                "model": {"provider": "openai", "model_id": "gpt-4o-mini"},
            },
            "input_data": {"query": "test"},
            "upstream_outputs": {},
        }
        result = await executor.execute(context)
        # Should fall back to echo since no API key
        assert result["error"] is None
        assert "response" in result["output"]

    @pytest.mark.asyncio
    async def test_llm_call_success(self):
        """Mock successful LLM call and verify cost tracking."""
        executor = AgentNodeExecutor()

        mock_response = MagicMock()
        mock_response.content = "The answer is 42."
        mock_response.usage = {"input_tokens": 100, "output_tokens": 20, "cost": 0.005}

        with patch("app.engine.executors.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response

            context = {
                "node_id": "agent_1",
                "config": {
                    "system_prompt": "Answer questions.",
                    "model": {"provider": "openai", "model_id": "gpt-4o-mini", "temperature": 0.1},
                },
                "input_data": {"query": "What is the meaning of life?"},
                "upstream_outputs": {},
            }
            result = await executor.execute(context)

            assert result["output"]["response"] == "The answer is 42."
            assert result["tokens_in"] == 100
            assert result["tokens_out"] == 20
            assert result["cost_usd"] == 0.005
            assert result["error"] is None

    @pytest.mark.asyncio
    async def test_llm_call_failure(self):
        """Mock failed LLM call and verify error handling."""
        executor = AgentNodeExecutor()

        with patch("app.engine.executors.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("Rate limit exceeded")

            context = {
                "node_id": "agent_1",
                "config": {"system_prompt": "test", "model": {"provider": "openai", "model_id": "gpt-4o-mini"}},
                "input_data": {},
                "upstream_outputs": {},
            }
            result = await executor.execute(context)
            assert result["error"] is not None
            assert "Rate limit" in result["error"]


class TestRouterNodeExecutor:
    """Test router with safeeval (NO eval())."""

    @pytest.mark.asyncio
    async def test_conditional_routing_match(self):
        executor = RouterNodeExecutor()
        context = {
            "node_id": "router_1",
            "config": {
                "routing_mode": "conditional",
                "conditions": [
                    {"name": "billing", "expression": "upstream['classifier']['intent'] == 'billing'"},
                    {"name": "technical", "expression": "upstream['classifier']['intent'] == 'technical'"},
                ],
            },
            "upstream_outputs": {
                "classifier": {"intent": "billing"},
            },
        }
        result = await executor.execute(context)
        assert result["output"]["selected_route"] == "billing"

    @pytest.mark.asyncio
    async def test_conditional_routing_no_match(self):
        executor = RouterNodeExecutor()
        context = {
            "node_id": "router_1",
            "config": {
                "routing_mode": "conditional",
                "conditions": [
                    {"name": "billing", "expression": "upstream['x']['y'] == 'z'"},
                ],
            },
            "upstream_outputs": {"x": {"y": "a"}},
        }
        result = await executor.execute(context)
        assert result["output"]["selected_route"] is None

    @pytest.mark.asyncio
    async def test_safeeval_blocks_malicious_expression(self):
        """Verify simpleeval blocks code execution attempts."""
        executor = RouterNodeExecutor()
        context = {
            "node_id": "router_1",
            "config": {
                "routing_mode": "conditional",
                "conditions": [
                    # This would work with eval() but MUST fail with simpleeval
                    {"name": "evil", "expression": "__import__('os').system('echo pwned')"},
                ],
            },
            "upstream_outputs": {},
        }
        result = await executor.execute(context)
        # Should not match (expression evaluation fails safely)
        assert result["output"]["selected_route"] is None

    @pytest.mark.asyncio
    async def test_arithmetic_expressions(self):
        """simpleeval supports arithmetic — verify it works."""
        executor = RouterNodeExecutor()
        context = {
            "node_id": "router_1",
            "config": {
                "routing_mode": "conditional",
                "conditions": [
                    {"name": "high_cost", "expression": "2 + 3 > 4"},
                ],
            },
            "upstream_outputs": {},
        }
        result = await executor.execute(context)
        assert result["output"]["selected_route"] == "high_cost"


class TestEvaluatorNodeExecutor:
    """Test evaluator with schema validation and LLM-as-judge."""

    @pytest.mark.asyncio
    async def test_schema_only_mode(self):
        executor = EvaluatorNodeExecutor()
        context = {
            "node_id": "eval_1",
            "config": {
                "evaluation_mode": "schema_only",
                "criteria": [{"name": "completeness"}, {"name": "accuracy"}],
                "passing_threshold": 0.7,
            },
            "upstream_outputs": {},
        }
        result = await executor.execute(context)
        assert result["output"]["passed"] is True
        assert result["output"]["mode"] == "schema_only"
        assert len(result["output"]["details"]) == 2

    @pytest.mark.asyncio
    async def test_llm_judge_tracks_costs(self):
        """LLM-as-judge should track its own token costs."""
        executor = EvaluatorNodeExecutor()

        mock_response = MagicMock()
        mock_response.content = json.dumps({"scores": [{"name": "quality", "score": 0.9, "passed": True}]})
        mock_response.usage = {"input_tokens": 200, "output_tokens": 50, "cost": 0.01}

        with patch("app.engine.executors.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response

            context = {
                "node_id": "eval_1",
                "config": {
                    "evaluation_mode": "llm_judge",
                    "criteria": [{"name": "quality"}],
                    "passing_threshold": 0.7,
                    "judge_model": {"provider": "openai", "model_id": "gpt-4o-mini"},
                },
                "upstream_outputs": {"agent_1": {"response": "test"}},
            }
            result = await executor.execute(context)
            assert result["tokens_in"] == 200
            assert result["tokens_out"] == 50
            assert result["cost_usd"] == 0.01


class TestHITLNodeExecutor:
    """Test HITL with Redis polling (real implementation)."""

    @pytest.mark.asyncio
    async def test_auto_approve_on_redis_failure(self):
        """When Redis is unavailable, HITL should auto-approve."""
        executor = HITLNodeExecutor()
        context = {
            "node_id": "hitl_1",
            "run_id": "test_run_123",
            "config": {"approval_mode": "approve_reject", "timeout_hours": 0.001},
            "upstream_outputs": {},
        }

        with patch("app.engine.executors.aioredis") as mock_redis:
            mock_redis.from_url.side_effect = Exception("Redis connection failed")
            result = await executor.execute(context)
            assert result["output"]["decision"] == "auto_approved"

    @pytest.mark.asyncio
    async def test_timeout_rejects(self):
        """When timeout expires without response, should reject."""
        executor = HITLNodeExecutor()
        executor.POLL_INTERVAL = 0.1  # Speed up for testing
        context = {
            "node_id": "hitl_1",
            "run_id": "test_run_456",
            "config": {"approval_mode": "approve_reject", "timeout_hours": 0.0001},
            "upstream_outputs": {},
        }

        mock_redis_client = AsyncMock()
        mock_redis_client.get = AsyncMock(return_value=None)  # No response
        mock_redis_client.aclose = AsyncMock()

        with patch("app.engine.executors.aioredis") as mock_redis:
            mock_redis.from_url.return_value = mock_redis_client
            result = await executor.execute(context)
            assert result["output"]["decision"] == "timeout_rejected"


class TestToolNodeExecutor:
    """Test tool node with stub and MCP client."""

    @pytest.mark.asyncio
    async def test_stub_mode(self):
        """When MCP client not available, should use stub."""
        executor = ToolNodeExecutor()
        context = {
            "node_id": "tool_1",
            "config": {
                "tool": {"server": "web-search", "tool": "search"},
                "input_mapping": {"query": "test query"},
            },
            "upstream_outputs": {},
        }
        result = await executor.execute(context)
        assert result["error"] is None
        assert "result" in result["output"]


# ─── Integration: Full Pipeline ────────────────────────────────────


class TestEndToEndPipeline:
    """Test a complete workflow execution with mocked LLM."""

    @pytest.mark.asyncio
    async def test_simple_workflow_execution(self):
        """Compile and execute a simple Input → Agent → Output workflow."""
        dag = {
            "nodes": [
                {"id": "input", "type": "input", "config": {}},
                {"id": "agent", "type": "agent", "config": {
                    "system_prompt": "Answer briefly.",
                    "model": {"provider": "openai", "model_id": "gpt-4o-mini"},
                }},
                {"id": "output", "type": "output", "config": {}},
            ],
            "edges": [
                {"source": "input", "target": "agent"},
                {"source": "agent", "target": "output"},
            ],
        }

        # Validate first
        validator = DAGValidator(dag)
        assert validator.validate()["valid"]

        # Compile
        executors = get_default_executors()
        compiler = WorkflowCompiler(dag, executors)
        graph = compiler.compile()

        # Execute with mocked LLM
        mock_response = MagicMock()
        mock_response.content = "42"
        mock_response.usage = {"input_tokens": 50, "output_tokens": 5, "cost": 0.001}

        with patch("app.engine.executors.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response

            initial_state = {
                "run_id": "test_run",
                "workflow_id": "test_wf",
                "status": "running",
                "input_data": {"query": "meaning of life?"},
                "node_results": {},
                "global_context": {},
                "total_tokens_in": 0,
                "total_tokens_out": 0,
                "total_cost_usd": 0.0,
                "error": None,
            }

            final_state = await graph.ainvoke(initial_state)

            assert final_state["total_tokens_in"] == 50
            assert final_state["total_tokens_out"] == 5
            assert final_state["total_cost_usd"] == 0.001
            assert "agent" in final_state["node_results"]
            assert final_state["node_results"]["agent"]["output"]["response"] == "42"
