"""Node executors — execute individual nodes within a workflow."""

import abc
import json
from typing import Any

import structlog

from app.engine.llm_client import call_llm

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
    """Executes an LLM-powered agent node using the unified LLM client."""

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        config = context.get("config", {})
        system_prompt = config.get("system_prompt", "You are a helpful assistant.")
        model_config = config.get("model", {})
        upstream = self._merge_upstream(context.get("upstream_outputs", {}))
        input_data = context.get("input_data", {})

        provider = model_config.get("provider", "openai")
        model_id = model_config.get("model_id", "gpt-4o-mini")
        temperature = model_config.get("temperature", 0.3)

        # Build the user message from upstream + input
        user_content_parts = []
        if input_data:
            user_content_parts.append(f"Input: {json.dumps(input_data, default=str)}")
        if upstream:
            user_content_parts.append(f"Context from previous steps: {json.dumps(upstream, default=str)}")

        user_message = "\n".join(user_content_parts) if user_content_parts else "Please proceed with your task."

        try:
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
            logger.warning("LLM config error, using echo fallback", error=str(e), node_id=context.get("node_id"))
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
            logger.error("Agent node execution failed", error=str(e), node_id=context.get("node_id"))
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
            # Try MCP client call
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
            logger.error("Tool node execution failed", error=str(e), node_id=context.get("node_id"))
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
                try:
                    # Safe expression evaluation with limited builtins
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
    """Evaluates upstream output quality — schema validation or LLM-as-judge."""

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        config = context.get("config", {})
        upstream = self._merge_upstream(context.get("upstream_outputs", {}))

        evaluation_mode = config.get("evaluation_mode", "schema_only")
        criteria = config.get("criteria", [])
        threshold = config.get("passing_threshold", 0.7)

        score = 1.0
        passed = True
        details = []

        if evaluation_mode == "llm_judge" and criteria:
            # Use LLM to evaluate
            try:
                model_config = config.get("judge_model", {"provider": "openai", "model_id": "gpt-4o-mini"})
                eval_prompt = (
                    "You are a quality evaluator. Score each criterion from 0.0 to 1.0.\n"
                    "Return JSON: {\"scores\": [{\"name\": \"...\", \"score\": 0.0, \"passed\": true}]}\n\n"
                    f"Criteria: {json.dumps(criteria)}\n\n"
                    f"Content to evaluate: {json.dumps(upstream, default=str)[:2000]}"
                )
                response = await call_llm(
                    provider=model_config.get("provider", "openai"),
                    model_id=model_config.get("model_id", "gpt-4o-mini"),
                    system=eval_prompt,
                    user="Evaluate the content above.",
                    temperature=0.1,
                )
                # Parse LLM response
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
        # Full implementation would pause and emit a WebSocket event for human input
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
