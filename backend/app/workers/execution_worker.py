"""Background execution worker — picks up jobs from Redis queue and runs them.

Responsibilities:
- Poll Redis for pending execution jobs
- Compile DAG → LangGraph StateGraph
- Execute with OTel tracing + Langfuse logging
- Persist results, cost records, and node execution traces
- Emit WebSocket events for real-time monitoring
- Check budget limits before execution
- Handle graceful shutdown
"""

import asyncio
import json
import signal
from datetime import datetime, timezone

import redis.asyncio as redis
import structlog
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.engine.compiler import WorkflowCompiler
from app.engine.executors import get_default_executors
from app.models.execution import Execution, ExecutionNode
from app.models.misc import CostRecord
from app.models.workflow import Workflow
from app.services.tracing import get_tracer, span_workflow_execution
from app.services.langfuse_integration import trace_workflow, trace_node
from app.services.budget import check_budget, check_node_budget

logger = structlog.get_logger()
settings = get_settings()

# Graceful shutdown flag
_shutdown_event = asyncio.Event()

# Shared Redis client for WebSocket event emission (avoids connection churn)
_shared_redis_client: redis.Redis | None = None


async def _get_shared_redis() -> redis.Redis:
    """Get or create the shared Redis client for event emission."""
    global _shared_redis_client
    if _shared_redis_client is None:
        _shared_redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _shared_redis_client


def _handle_signal(signum, frame):
    logger.info("Shutdown signal received", signal=signum)
    _shutdown_event.set()


async def execute_workflow(execution_id: str) -> None:
    """Execute a workflow given its execution ID."""
    async with async_session_factory() as db:
        # Load execution record
        result = await db.execute(select(Execution).where(Execution.id == execution_id))
        execution = result.scalar_one_or_none()
        if not execution:
            logger.error("Execution not found", execution_id=execution_id)
            return

        # Load workflow
        result = await db.execute(select(Workflow).where(Workflow.id == execution.workflow_id))
        workflow = result.scalar_one_or_none()
        if not workflow:
            logger.error("Workflow not found", workflow_id=execution.workflow_id)
            execution.status = "failed"
            execution.error = {"message": "Workflow not found"}
            await db.commit()
            return

        # Budget check before execution
        budget_result = await check_budget(
            workflow_id=workflow.id,
            workspace_id=workflow.workspace_id,
            db=db,
        )
        if not budget_result["allowed"]:
            logger.warning("Budget check failed", execution_id=execution_id, errors=budget_result["errors"])
            execution.status = "failed"
            execution.error = {"message": "Budget exceeded", "details": budget_result["errors"]}
            await db.commit()
            return

        # Update status to running
        execution.status = "running"
        execution.started_at = datetime.now(timezone.utc)
        await db.commit()

        # Emit WebSocket event: execution started
        await _emit_ws_event(execution_id, {
            "type": "execution_started",
            "workflow_id": workflow.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # OTel span for the full workflow execution
        tracer = get_tracer()
        with span_workflow_execution(tracer, workflow.id, execution_id):
            try:
                # Compile the workflow
                dag = workflow.dag_json
                executors = get_default_executors()
                compiler = WorkflowCompiler(dag, executors)
                compiled_graph = compiler.compile()

                # Initial state — pass run_id so HITL executor can poll Redis
                initial_state = {
                    "run_id": execution_id,
                    "workflow_id": workflow.id,
                    "status": "running",
                    "input_data": execution.input_data or {},
                    "node_results": {},
                    "global_context": {},
                    "total_tokens_in": 0,
                    "total_tokens_out": 0,
                    "total_cost_usd": 0.0,
                    "error": None,
                }

                # Execute the graph
                final_state = await compiled_graph.ainvoke(initial_state)

                # Update execution with results
                execution.status = "completed"
                execution.completed_at = datetime.now(timezone.utc)
                execution.output_data = final_state.get("node_results", {})
                execution.total_tokens_in = final_state.get("total_tokens_in", 0)
                execution.total_tokens_out = final_state.get("total_tokens_out", 0)
                execution.total_cost_usd = final_state.get("total_cost_usd", 0.0)

                # Save individual node execution records + cost records
                for node_id, node_result in final_state.get("node_results", {}).items():
                    node_status = "completed" if not node_result.get("error") else "failed"
                    node_record = ExecutionNode(
                        execution_id=execution_id,
                        node_id=node_id,
                        node_name=node_id,
                        status=node_status,
                        input_json=final_state.get("input_data"),
                        output_json=node_result.get("output", {}),
                        tokens_in=node_result.get("tokens_in", 0),
                        tokens_out=node_result.get("tokens_out", 0),
                        cost_usd=node_result.get("cost_usd", 0.0),
                        error={"message": node_result["error"]} if node_result.get("error") else None,
                        started_at=execution.started_at,
                        completed_at=datetime.now(timezone.utc),
                    )
                    db.add(node_record)

                    # Persist cost record if there's a cost
                    if node_result.get("cost_usd", 0) > 0:
                        cost_record = CostRecord(
                            execution_id=execution_id,
                            workflow_id=workflow.id,
                            workspace_id=workflow.workspace_id,
                            node_id=node_id,
                            model="unknown",
                            tokens_in=node_result.get("tokens_in", 0),
                            tokens_out=node_result.get("tokens_out", 0),
                            cost_usd=node_result.get("cost_usd", 0.0),
                        )
                        db.add(cost_record)

                    # Langfuse: trace individual node
                    trace_node(
                        execution_id=execution_id,
                        node_id=node_id,
                        node_type=dag.get("nodes", {}).get(node_id, {}).get("type", "unknown") if isinstance(dag.get("nodes"), dict) else "unknown",
                        input_data=final_state.get("input_data"),
                        output_data=node_result.get("output", {}),
                        tokens_in=node_result.get("tokens_in", 0),
                        tokens_out=node_result.get("tokens_out", 0),
                        cost_usd=node_result.get("cost_usd", 0.0),
                    )

                    # Emit WebSocket event: node completed
                    await _emit_ws_event(execution_id, {
                        "type": "node_completed" if node_status == "completed" else "node_failed",
                        "node_id": node_id,
                        "status": node_status,
                        "tokens_in": node_result.get("tokens_in", 0),
                        "tokens_out": node_result.get("tokens_out", 0),
                        "cost_usd": node_result.get("cost_usd", 0.0),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

                # Langfuse: trace full workflow
                trace_workflow(
                    execution_id=execution_id,
                    workflow_id=workflow.id,
                    workflow_name=workflow.name,
                    input_data=execution.input_data,
                    output_data=execution.output_data,
                    total_cost=execution.total_cost_usd,
                    total_tokens=execution.total_tokens_in + execution.total_tokens_out,
                    status="completed",
                )

                logger.info(
                    "Workflow execution completed",
                    execution_id=execution_id,
                    tokens_in=execution.total_tokens_in,
                    tokens_out=execution.total_tokens_out,
                    cost=execution.total_cost_usd,
                )

                # Emit WebSocket event: execution completed
                await _emit_ws_event(execution_id, {
                    "type": "execution_completed",
                    "total_tokens_in": execution.total_tokens_in,
                    "total_tokens_out": execution.total_tokens_out,
                    "total_cost_usd": execution.total_cost_usd,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            except Exception as e:
                logger.error("Workflow execution failed", execution_id=execution_id, error=str(e))
                execution.status = "failed"
                execution.completed_at = datetime.now(timezone.utc)
                execution.error = {"message": str(e), "type": type(e).__name__}

                # Langfuse: trace failed workflow
                trace_workflow(
                    execution_id=execution_id,
                    workflow_id=workflow.id,
                    workflow_name=workflow.name,
                    input_data=execution.input_data,
                    total_cost=0.0,
                    total_tokens=0,
                    status="failed",
                    metadata={"error": str(e)},
                )

                # Emit WebSocket event: execution failed
                await _emit_ws_event(execution_id, {
                    "type": "execution_failed",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        await db.commit()


async def _emit_ws_event(run_id: str, event: dict) -> None:
    """Publish a WebSocket event via Redis pub/sub.

    Uses a shared Redis client to avoid connection churn.
    """
    try:
        redis_client = await _get_shared_redis()
        channel = f"agentforge:ws:{run_id}"
        await redis_client.publish(channel, json.dumps(event, default=str))
    except Exception as e:
        logger.debug("Failed to emit WS event", error=str(e), run_id=run_id)


async def worker_loop() -> None:
    """Main worker loop — polls Redis for execution jobs with graceful shutdown.
    
    Can be run standalone (python -m app.workers.execution_worker) or embedded
    in FastAPI's lifespan as an asyncio task.
    """
    global _shared_redis_client
    logger.info("Execution worker started")
    
    # Use shared Redis client for both polling and event emission
    redis_client = await _get_shared_redis()

    try:
        while not _shutdown_event.is_set():
            try:
                # BLPOP blocks until a job is available (timeout 1s)
                result = await redis_client.blpop("agentforge:executions", timeout=1)
                if result:
                    _, execution_id = result
                    logger.info("Picked up execution job", execution_id=execution_id)
                    await execute_workflow(execution_id)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Worker loop error", error=str(e))
                await asyncio.sleep(5)
    finally:
        # Clean up shared Redis client
        if _shared_redis_client:
            await _shared_redis_client.aclose()
            _shared_redis_client = None
        logger.info("Execution worker shut down gracefully")


async def main():
    """Entry point for standalone execution worker."""
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    await worker_loop()


if __name__ == "__main__":
    asyncio.run(main())
