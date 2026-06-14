"""Langfuse integration — export traces and generations to Langfuse for LLM observability.

Compatible with langfuse v4.x. Uses the Langfuse client directly for tracing.
"""

from typing import Any

import structlog
from langfuse import Langfuse

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

_langfuse: Langfuse | None = None


def get_langfuse() -> Langfuse | None:
    """Get or create the Langfuse client. Returns None if not configured."""
    global _langfuse
    if _langfuse is not None:
        return _langfuse

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.info("Langfuse not configured (LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY)")
        return None

    try:
        _langfuse = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        logger.info("Langfuse initialized", host=settings.langfuse_host)
        return _langfuse
    except Exception as e:
        logger.error("Langfuse init failed", error=str(e))
        return None


def trace_workflow(
    execution_id: str,
    workflow_id: str,
    workflow_name: str,
    input_data: dict | None = None,
    output_data: dict | None = None,
    metadata: dict | None = None,
    total_cost: float = 0.0,
    total_tokens: int = 0,
    status: str = "completed",
) -> None:
    """Log a completed workflow execution to Langfuse as a trace."""
    lf = get_langfuse()
    if lf is None:
        return

    try:
        lf.trace(
            id=execution_id,
            name=f"workflow:{workflow_name}",
            session_id=workflow_id,
            input=input_data,
            output=output_data,
            metadata={
                **(metadata or {}),
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "status": status,
            },
            tags=["workflow", status],
        )
        logger.info("Langfuse trace created", execution_id=execution_id)
    except Exception as e:
        logger.error("Langfuse trace failed", error=str(e))


def trace_node(
    execution_id: str,
    node_id: str,
    node_type: str,
    input_data: dict | None = None,
    output_data: dict | None = None,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_usd: float = 0.0,
    model: str | None = None,
) -> None:
    """Log a node execution to Langfuse as a span within the workflow trace."""
    lf = get_langfuse()
    if lf is None:
        return

    try:
        if node_type == "agent" and model:
            lf.generation(
                trace_id=execution_id,
                name=f"node:{node_id}",
                model=model,
                input=input_data,
                output=output_data,
                usage={
                    "input": tokens_in,
                    "output": tokens_out,
                    "totalCost": cost_usd,
                },
                metadata={"node_id": node_id, "node_type": node_type},
            )
        else:
            lf.span(
                trace_id=execution_id,
                name=f"node:{node_id}:{node_type}",
                input=input_data,
                output=output_data,
                metadata={
                    "node_id": node_id,
                    "node_type": node_type,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cost_usd": cost_usd,
                },
            )
    except Exception as e:
        logger.error("Langfuse node trace failed", error=str(e))


def flush() -> None:
    """Flush pending Langfuse events. Call during shutdown."""
    if _langfuse:
        _langfuse.flush()
        logger.info("Langfuse flushed")
