"""OpenTelemetry instrumentation for AgentForge.

Adds distributed tracing spans for:
- Workflow execution (top-level span)
- Individual node execution (child spans)
- LLM API calls (grandchild spans)
- MCP tool calls (grandchild spans)
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource

from app.core.config import get_settings

settings = get_settings()


def setup_tracing() -> trace.Tracer:
    """Initialize OpenTelemetry tracing and return a tracer.

    Call this during app startup (in lifespan).
    """
    resource = Resource.create({
        "service.name": "agentforge",
        "service.version": settings.app_version,
        "deployment.environment": settings.environment,
    })

    provider = TracerProvider(resource=resource)

    # Console exporter for development
    if settings.environment == "development":
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    # OTLP exporter for production (if endpoint configured)
    if settings.otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        otlp_exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    trace.set_tracer_provider(provider)
    return trace.get_tracer("agentforge")


def get_tracer() -> trace.Tracer:
    """Get the global tracer instance."""
    return trace.get_tracer("agentforge")


# ─── Span helpers ──────────────────────────────────────────────────


def span_workflow_execution(tracer: trace.Tracer, workflow_id: str, execution_id: str):
    """Create a top-level span for a workflow execution."""
    return tracer.start_as_current_span(
        "workflow.execute",
        attributes={
            "agentforge.workflow_id": workflow_id,
            "agentforge.execution_id": execution_id,
        },
    )


def span_node_execution(tracer: trace.Tracer, node_id: str, node_type: str):
    """Create a child span for a node execution."""
    return tracer.start_as_current_span(
        f"node.{node_type}",
        attributes={
            "agentforge.node_id": node_id,
            "agentforge.node_type": node_type,
        },
    )


def span_llm_call(tracer: trace.Tracer, provider: str, model: str):
    """Create a span for an LLM API call."""
    return tracer.start_as_current_span(
        "llm.call",
        attributes={
            "gen_ai.system": provider,
            "gen_ai.request.model": model,
        },
    )


def span_mcp_call(tracer: trace.Tracer, server: str, tool: str):
    """Create a span for an MCP tool call."""
    return tracer.start_as_current_span(
        "mcp.tool_call",
        attributes={
            "agentforge.mcp_server": server,
            "agentforge.mcp_tool": tool,
        },
    )
