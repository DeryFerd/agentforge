"""Node executors — execute individual nodes within a workflow."""

import abc
from typing import Any

import structlog

logger = structlog.get_logger()


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


class InputNodeExecutor(BaseNodeExecutor):
    """Passes workflow input data through."""

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
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
        upstream = self._merge_upstream(context.get("upstream_outputs", {}))
        return {
            "output": {"result": upstream},
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_usd": 0.0,
            "error": None,
        }


class AgentNodeExecutor(BaseNodeExecutor):
    """Executes an LLM-powered agent node."""

    def __init__(self, llm_provider: Any = None):
        self.llm_provider = llm_provider

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        config = context.get("config", {})
        system_prompt = config.get("system_prompt", "You are a helpful assistant.")
        model_config = config.get("model", {})
        upstream = self._merge_upstream(context.get("upstream_outputs", {}))
        input_data = context.get("input_data", {})

        # Build the user message from upstream + input
        user_content_parts = []
        if input_data:
            user_content_parts.append(f"Input: {input_data}")
        if upstream:
            user_content_parts.append(f"Context from previous steps: {upstream}")

        user_message = "\n".join(user_content_parts) if user_content_parts else "Please proceed with your task."

        try:
            # Try to call LLM
            if self.llm_provider:
                response = await self.llm_provider.acall(
                    model=model_config.get("model_id", "gpt-4o-mini"),
                    system=system_prompt,
                    user=user_message,
                    temperature=model_config.get("temperature", 0.3),
                )
                return {
                    "output": {"response": response.content},
                    "tokens_in": response.usage.get("input_tokens", 0),
                    "tokens_out": response.usage.get("output_tokens", 0),
                    "cost_usd": response.usage.get("cost", 0.0),
                    "error": None,
                }
            else:
                # Fallback: echo mode for development without LLM keys
                logger.warning("No LLM provider configured, returning echo response")
                return {
                    "output": {
                        "response": f"[Agent Echo] System: {system_prompt}\nUser: {user_message}",
                        "mode": "echo",
                    },
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "cost_usd": 0.0,
                    "error": None,
                }
        except Exception as e:
            logger.error("Agent node execution failed", error=str(e), node_id=context.get("node_id"))
            return {
                "output": {},
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
                "error": str(e),
            }


class ToolNodeExecutor(BaseNodeExecutor):
    """Calls an external tool (MCP server or HTTP API)."""

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        config = context.get("config", {})
        tool_config = config.get("tool", {})
        upstream = self._merge_upstream(context.get("upstream_outputs", {}))

        # Resolve input mappings
        input_mapping = config.get("input_mapping", {})
        resolved_params = {}
        for param_name, template in input_mapping.items():
            if isinstance(template, str) and "{{" in template:
                # Simple template resolution
                resolved = template
                for key, value in upstream.items():
                    resolved = resolved.replace(f"{{{{upstream.{key}}}}}", str(value))
                resolved_params[param_name] = resolved
            else:
                resolved_params[param_name] = template

        try:
            # TODO: Actual MCP tool call (Phase 6)
            logger.info(
                "Tool node called",
                server=tool_config.get("server"),
                tool=tool_config.get("tool"),
                params=resolved_params,
            )
            return {
                "output": {
                    "result": f"[Tool Call] {tool_config.get('server')}.{tool_config.get('tool')}({resolved_params})",
                    "mode": "stub",
                },
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
                "error": None,
            }
        except Exception as e:
            return {
                "output": {},
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
                "error": str(e),
            }


class RouterNodeExecutor(BaseNodeExecutor):
    """Routes to different downstream paths based on conditions."""

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        config = context.get("config", {})
        upstream = self._merge_upstream(context.get("upstream_outputs", {}))

        routing_mode = config.get("routing_mode", "conditional")
        conditions = config.get("conditions", [])

        selected_route = None
        if routing_mode == "conditional":
            for condition in conditions:
                expression = condition.get("expression", "")
                # Simple expression evaluation for MVP
                # Full implementation would use a safe expression evaluator
                try:
                    if eval(expression, {"__builtins__": {}}, {"upstream": upstream}):
                        selected_route = condition.get("name")
                        break
                except Exception:
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
    """Evaluates upstream output quality."""

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        config = context.get("config", {})
        upstream = self._merge_upstream(context.get("upstream_outputs", {}))

        evaluation_mode = config.get("evaluation_mode", "schema_only")
        criteria = config.get("criteria", [])
        threshold = config.get("passing_threshold", 0.7)

        # Simple schema validation for MVP
        score = 1.0
        passed = True
        details = []

        for criterion in criteria:
            # TODO: LLM-as-judge evaluation (Phase 4)
            details.append({"criterion": criterion.get("name"), "score": 1.0, "passed": True})

        return {
            "output": {
                "passed": passed,
                "score": score,
                "threshold": threshold,
                "details": details,
            },
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_usd": 0.0,
            "error": None,
        }


class HITLNodeExecutor(BaseNodeExecutor):
    """Pauses for human review/input."""

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        config = context.get("config", {})

        # In MVP, HITL nodes auto-approve
        # Full implementation would pause and wait for human input
        return {
            "output": {
                "decision": "auto_approved",
                "approval_mode": config.get("approval_mode", "approve_reject"),
                "mode": "auto_approve_mvp",
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
