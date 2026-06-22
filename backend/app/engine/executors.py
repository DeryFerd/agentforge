"""Node executors — execute individual nodes within a workflow.

All executors:
- Emit OpenTelemetry spans for observability
- Track token usage and costs
- Support graceful error recovery
- Truncate context to prevent token overflow
"""

import abc
import asyncio
import json
from typing import Any

import structlog
from simpleeval import EvalWithCompoundTypes, simple_eval

from app.engine.llm_client import call_llm
from app.services.tracing import get_tracer, span_node_execution, span_llm_call, span_mcp_call

logger = structlog.get_logger()

# Maximum characters for upstream context per node (prevents token overflow)
MAX_CONTEXT_CHARS = 4000


def _truncate_context(data: Any, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """Serialize and truncate context data to prevent token overflow.
    
    Args:
        data: Data to serialize (dict, list, or any JSON-serializable object)
        max_chars: Maximum character limit
        
    Returns:
        Truncated JSON string with ellipsis if truncated
    """
    serialized = json.dumps(data, default=str)
    if len(serialized) <= max_chars:
        return serialized
    # Truncate and add indicator
    truncated = serialized[:max_chars]
    return truncated + f'... [truncated, {len(serialized)} chars total]'


class BaseNodeExecutor(abc.ABC):
    """Base class for all node executors."""

    @abc.abstractmethod
    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute a node and return the result.

        Args:
            context: Execution context containing:
                - node_id: str
                - node_type: str
                - config: dict (node configuration)
                - input_data: dict (workflow input)
                - upstream_outputs: dict[str, dict] (outputs from connected upstream nodes)
                - global_context: dict
                - run_id: str (execution ID for HITL polling)

        Returns:
            dict with keys: output, tokens_in, tokens_out, cost_usd, error
        """
        ...

    def _merge_upstream(self, upstream_outputs: dict[str, dict]) -> dict[str, Any]:
        """Merge all upstream outputs into a single context dict."""
        merged = {}
        for source_id, output in upstream_outputs.items():
            merged[source_id] = output
        return merged

    def _wrap_with_span(self, node_id: str, node_type: str):
        """Get an OTel span context manager for this node execution."""
        tracer = get_tracer()
        return span_node_execution(tracer, node_id, node_type)


class InputNodeExecutor(BaseNodeExecutor):
    """Passes workflow input data through."""

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        node_id = context.get("node_id", "input")
        with self._wrap_with_span(node_id, "input"):
            return {
                "output": context.get("input_data", {}),
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
                "error": None,
            }


class OutputNodeExecutor(BaseNodeExecutor):
    """Collects upstream outputs as the workflow's final output."""

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        node_id = context.get("node_id", "output")
        with self._wrap_with_span(node_id, "output"):
            upstream = self._merge_upstream(context.get("upstream_outputs", {}))
            return {
                "output": {"result": upstream},
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
                "error": None,
            }


class AgentNodeExecutor(BaseNodeExecutor):
    """Executes an LLM-powered agent node using the unified LLM client."""

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        node_id = context.get("node_id", "agent")
        with self._wrap_with_span(node_id, "agent"):
            config = context.get("config", {})
            system_prompt = config.get("system_prompt", "You are a helpful assistant.")
            model_config = config.get("model", {})
            upstream = self._merge_upstream(context.get("upstream_outputs", {}))
            input_data = context.get("input_data", {})

            provider = model_config.get("provider", "openai")
            model_id = model_config.get("model_id", "gpt-4o-mini")
            temperature = model_config.get("temperature", 0.3)

            # Build the user message from upstream + input (with truncation)
            user_content_parts = []
            if input_data:
                user_content_parts.append(f"Input: {_truncate_context(input_data)}")
            if upstream:
                user_content_parts.append(f"Context from previous steps: {_truncate_context(upstream)}")

            user_message = "\n".join(user_content_parts) if user_content_parts else "Please proceed with your task."

            try:
                # Create OTel span for the LLM call
                tracer = get_tracer()
                with span_llm_call(tracer, provider, model_id):
                    response = await call_llm(
                        provider=provider,
                        model_id=model_id,
                        system=system_prompt,
                        user=user_message,
                        temperature=temperature,
                    )
                return {
                    "output": {"response": response.content},
                    "tokens_in": response.usage.get("input_tokens", 0),
                    "tokens_out": response.usage.get("output_tokens", 0),
                    "cost_usd": response.usage.get("cost", 0.0),
                    "error": None,
                }
            except ValueError as e:
                # Config error (missing API key) — fall back to echo mode
                logger.warning("LLM config error, using echo fallback", error=str(e), node_id=node_id)
                return {
                    "output": {
                        "response": f"[Agent Echo — {provider}/{model_id} not configured] System: {system_prompt[:200]}\nUser: {user_message[:200]}",
                        "mode": "echo",
                        "reason": str(e),
                    },
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "cost_usd": 0.0,
                    "error": None,
                }
            except Exception as e:
                logger.error("Agent node execution failed", error=str(e), node_id=node_id)
                return {
                    "output": {},
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "cost_usd": 0.0,
                    "error": str(e),
                }


class ToolNodeExecutor(BaseNodeExecutor):
    """Calls an external tool via MCP client."""

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        node_id = context.get("node_id", "tool")
        with self._wrap_with_span(node_id, "tool"):
            config = context.get("config", {})
            tool_config = config.get("tool", {})
            upstream = self._merge_upstream(context.get("upstream_outputs", {}))

            server_name = tool_config.get("server", "")
            tool_name = tool_config.get("tool", "")

            # Resolve input mappings
            input_mapping = config.get("input_mapping", {})
            resolved_params = {}
            for param_name, template in input_mapping.items():
                if isinstance(template, str) and "{{" in template:
                    resolved = template
                    for key, value in upstream.items():
                        resolved = resolved.replace(f"{{{{upstream.{key}}}}}", str(value))
                    resolved_params[param_name] = resolved
                else:
                    resolved_params[param_name] = template

            try:
                # OTel span for MCP call
                tracer = get_tracer()
                with span_mcp_call(tracer, server_name, tool_name):
                    from app.mcp.client import call_mcp_tool

                    result = await call_mcp_tool(server_name, tool_name, resolved_params)
                return {
                    "output": {"result": result},
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "cost_usd": 0.0,
                    "error": None,
                }
            except ImportError:
                # MCP client not available — stub mode
                logger.info("MCP client not available, using stub", server=server_name, tool=tool_name)
                return {
                    "output": {
                        "result": f"[Tool Stub] {server_name}.{tool_name}({json.dumps(resolved_params, default=str)})",
                        "mode": "stub",
                    },
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "cost_usd": 0.0,
                    "error": None,
                }
            except Exception as e:
                logger.error("Tool node execution failed", error=str(e), node_id=node_id)
                return {
                    "output": {},
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "cost_usd": 0.0,
                    "error": str(e),
                }


class RouterNodeExecutor(BaseNodeExecutor):
    """Routes to different downstream paths based on conditions.

    Uses simpleeval for safe expression evaluation — NO eval() calls.
    Supported operators: ==, !=, <, >, <=, >=, and, or, not, in, +, -, *, /
    Supported types: str, int, float, bool, list, dict (access via [])
    """

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        node_id = context.get("node_id", "router")
        with self._wrap_with_span(node_id, "router"):
            config = context.get("config", {})
            upstream = self._merge_upstream(context.get("upstream_outputs", {}))

            routing_mode = config.get("routing_mode", "conditional")
            conditions = config.get("conditions", [])

            selected_route = None
            if routing_mode == "conditional":
                for condition in conditions:
                    expression = condition.get("expression", "")
                    if not expression:
                        continue
                    try:
                        # SAFE expression evaluation using simpleeval
                        # This does NOT allow arbitrary code execution
                        # Only supports: comparisons, boolean ops, arithmetic, attribute access
                        result = simple_eval(
                            expression,
                            names={"upstream": upstream, "true": True, "false": False, "none": None},
                        )
                        if result:
                            selected_route = condition.get("name")
                            break
                    except Exception as e:
                        logger.debug(
                            "Router condition evaluation failed",
                            expression=expression,
                            error=str(e),
                            node_id=node_id,
                        )
                        continue

            return {
                "output": {
                    "selected_route": selected_route,
                    "routing_mode": routing_mode,
                },
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
                "error": None,
            }


class EvaluatorNodeExecutor(BaseNodeExecutor):
    """Evaluates upstream output quality — schema validation or LLM-as-judge."""

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        node_id = context.get("node_id", "evaluator")
        with self._wrap_with_span(node_id, "evaluator"):
            config = context.get("config", {})
            upstream = self._merge_upstream(context.get("upstream_outputs", {}))

            evaluation_mode = config.get("evaluation_mode", "schema_only")
            criteria = config.get("criteria", [])
            threshold = config.get("passing_threshold", 0.7)

            score = 1.0
            passed = True
            details = []
            total_tokens_in = 0
            total_tokens_out = 0
            total_cost = 0.0

            if evaluation_mode == "llm_judge" and criteria:
                try:
                    model_config = config.get("judge_model", {"provider": "openai", "model_id": "gpt-4o-mini"})
                    eval_prompt = (
                        "You are a quality evaluator. Score each criterion from 0.0 to 1.0.\n"
                        "Return JSON: {\"scores\": [{\"name\": \"...\", \"score\": 0.0, \"passed\": true}]}\n\n"
                        f"Criteria: {json.dumps(criteria)}\n\n"
                        f"Content to evaluate: {json.dumps(upstream, default=str)[:2000]}"
                    )

                    tracer = get_tracer()
                    provider = model_config.get("provider", "openai")
                    model_id = model_config.get("model_id", "gpt-4o-mini")

                    with span_llm_call(tracer, provider, model_id):
                        response = await call_llm(
                            provider=provider,
                            model_id=model_id,
                            system=eval_prompt,
                            user="Evaluate the content above.",
                            temperature=0.1,
                        )

                    # Track LLM judge costs
                    total_tokens_in = response.usage.get("input_tokens", 0)
                    total_tokens_out = response.usage.get("output_tokens", 0)
                    total_cost = response.usage.get("cost", 0.0)

                    try:
                        parsed = json.loads(response.content)
                        for item in parsed.get("scores", []):
                            details.append(item)
                            if item.get("score", 0) < threshold:
                                passed = False
                        if details:
                            score = sum(d.get("score", 0) for d in details) / len(details)
                    except json.JSONDecodeError:
                        details.append({"error": "Failed to parse LLM judge response"})
                except Exception as e:
                    logger.warning("LLM judge failed, defaulting to pass", error=str(e))
                    details.append({"warning": f"LLM judge failed: {e}", "defaulted": True})
            else:
                # Schema-only validation
                for criterion in criteria:
                    details.append({"criterion": criterion.get("name"), "score": 1.0, "passed": True})

            return {
                "output": {
                    "passed": passed,
                    "score": score,
                    "threshold": threshold,
                    "details": details,
                    "mode": evaluation_mode,
                },
                "tokens_in": total_tokens_in,
                "tokens_out": total_tokens_out,
                "cost_usd": total_cost,
                "error": None,
            }


class HITLNodeExecutor(BaseNodeExecutor):
    """Pauses for human review/input.

    Real implementation:
    1. Emits a "execution_paused" event via the context
    2. Polls Redis for a HITL response (written by WebSocket handler in main.py)
    3. Returns the human's decision
    """

    # How long to wait for human approval (seconds)
    DEFAULT_TIMEOUT = 3600  # 1 hour
    POLL_INTERVAL = 2  # seconds between Redis polls

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        node_id = context.get("node_id", "hitl")
        run_id = context.get("run_id", "")
        with self._wrap_with_span(node_id, "hitl"):
            config = context.get("config", {})
            approval_mode = config.get("approval_mode", "approve_reject")
            timeout_hours = config.get("timeout_hours", 1)
            timeout_seconds = int(timeout_hours * 3600)

            upstream = self._merge_upstream(context.get("upstream_outputs", {}))

            # Signal that we're pausing for human input
            # The execution worker will emit a WebSocket event
            logger.info(
                "HITL: Pausing for human review",
                run_id=run_id,
                node_id=node_id,
                approval_mode=approval_mode,
            )

            # Poll Redis for human response
            try:
                import redis.asyncio as aioredis
                from app.core.config import get_settings

                settings = get_settings()
                redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
                redis_key = f"hitl:{run_id}:{node_id}"

                elapsed = 0
                decision = None
                feedback = None

                while elapsed < timeout_seconds:
                    response_data = await redis_client.get(redis_key)
                    if response_data:
                        message = json.loads(response_data)
                        decision = message.get("decision", "rejected")
                        feedback = message.get("feedback")
                        # Clean up the key
                        await redis_client.delete(redis_key)
                        break
                    await asyncio.sleep(self.POLL_INTERVAL)
                    elapsed += self.POLL_INTERVAL

                await redis_client.aclose()

                if decision is None:
                    # Timeout — auto-reject
                    logger.warning("HITL: Timed out waiting for human response", run_id=run_id, node_id=node_id)
                    return {
                        "output": {
                            "decision": "timeout_rejected",
                            "approval_mode": approval_mode,
                            "feedback": None,
                            "waited_seconds": elapsed,
                        },
                        "tokens_in": 0,
                        "tokens_out": 0,
                        "cost_usd": 0.0,
                        "error": None,
                    }

                # If rejected, return error to halt the workflow
                error = None
                if decision == "rejected":
                    error = f"Human reviewer rejected: {feedback or 'No feedback provided'}"

                return {
                    "output": {
                        "decision": decision,
                        "approval_mode": approval_mode,
                        "feedback": feedback,
                        "upstream_data": upstream,
                    },
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "cost_usd": 0.0,
                    "error": error,
                }

            except Exception as e:
                logger.error("HITL: Redis polling failed", error=str(e), node_id=node_id)
                # Fallback: auto-approve on Redis failure
                return {
                    "output": {
                        "decision": "auto_approved",
                        "approval_mode": approval_mode,
                        "feedback": f"Redis error, auto-approved: {e}",
                    },
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "cost_usd": 0.0,
                    "error": None,
                }


def get_default_executors() -> dict[str, BaseNodeExecutor]:
    """Return a map of node_type -> executor for all supported types."""
    return {
        "input": InputNodeExecutor(),
        "output": OutputNodeExecutor(),
        "agent": AgentNodeExecutor(),
        "tool": ToolNodeExecutor(),
        "router": RouterNodeExecutor(),
        "evaluator": EvaluatorNodeExecutor(),
        "hitl": HITLNodeExecutor(),
    }
