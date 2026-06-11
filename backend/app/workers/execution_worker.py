"""Background execution worker — picks up jobs from Redis queue and runs them."""

import asyncio
import json
from datetime import datetime, timezone

import redis.asyncio as redis
import structlog
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.engine.compiler import WorkflowCompiler
from app.engine.executors import get_default_executors
from app.models.execution import Execution, ExecutionNode
from app.models.workflow import Workflow

logger = structlog.get_logger()
settings = get_settings()


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

        # Update status to running
        execution.status = "running"
        execution.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            # Compile the workflow
            dag = workflow.dag_json
            executors = get_default_executors()
            compiler = WorkflowCompiler(dag, executors)
            compiled_graph = compiler.compile()

            # Initial state
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

            # Save individual node execution records
            for node_id, node_result in final_state.get("node_results", {}).items():
                node_record = ExecutionNode(
                    execution_id=execution_id,
                    node_id=node_id,
                    node_name=node_id,
                    status="completed" if not node_result.get("error") else "failed",
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

            logger.info(
                "Workflow execution completed",
                execution_id=execution_id,
                tokens_in=execution.total_tokens_in,
                tokens_out=execution.total_tokens_out,
                cost=execution.total_cost_usd,
            )

        except Exception as e:
            logger.error("Workflow execution failed", execution_id=execution_id, error=str(e))
            execution.status = "failed"
            execution.completed_at = datetime.now(timezone.utc)
            execution.error = {"message": str(e), "type": type(e).__name__}

        await db.commit()


async def worker_loop() -> None:
    """Main worker loop — polls Redis for execution jobs."""
    logger.info("Execution worker started")
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)

    while True:
        try:
            # BLPOP blocks until a job is available (timeout 1s)
            result = await redis_client.blpop("agentforge:executions", timeout=1)
            if result:
                _, execution_id = result
                logger.info("Picked up execution job", execution_id=execution_id)
                await execute_workflow(execution_id)
        except Exception as e:
            logger.error("Worker loop error", error=str(e))
            await asyncio.sleep(5)


async def main():
    """Entry point for the execution worker."""
    await worker_loop()


if __name__ == "__main__":
    asyncio.run(main())
