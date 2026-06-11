"""Execution management endpoints."""

from datetime import datetime, timezone
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User
from app.models.execution import Execution, ExecutionNode
from app.models.workflow import Workflow

router = APIRouter()


class ExecuteRequest(BaseModel):
    input_data: dict = {}


class ExecutionResponse(BaseModel):
    id: str
    workflow_id: str
    status: str
    trigger_type: str
    total_cost_usd: float
    created_at: str
    completed_at: str | None
    model_config = {"from_attributes": True}


def _to_response(e: Execution) -> ExecutionResponse:
    return ExecutionResponse(
        id=e.id,
        workflow_id=e.workflow_id,
        status=e.status,
        trigger_type=e.trigger_type,
        total_cost_usd=e.total_cost_usd,
        created_at=str(e.created_at),
        completed_at=str(e.completed_at) if e.completed_at else None,
    )


@router.post("/workflows/{workflow_id}/execute", response_model=ExecutionResponse, status_code=201)
async def execute_workflow(
    workflow_id: str,
    body: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Trigger a new execution for a workflow."""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    execution = Execution(
        workflow_id=workflow_id,
        triggered_by=user.id,
        trigger_type="manual",
        status="queued",
        input_data=body.input_data,
        started_at=datetime.now(timezone.utc),
    )
    db.add(execution)
    await db.flush()
    await db.refresh(execution)

    # Enqueue to Redis for the worker to pick up
    try:
        redis_client = aioredis.from_url(get_settings().redis_url, decode_responses=True)
        await redis_client.rpush("agentforge:executions", execution.id)
        await redis_client.aclose()
    except Exception:
        # If Redis is unavailable, execution stays queued (worker will retry)
        pass

    return _to_response(execution)


@router.get("/workflows/{workflow_id}/executions", response_model=list[ExecutionResponse])
async def list_executions(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """List all executions for a workflow."""
    result = await db.execute(
        select(Execution)
        .where(Execution.workflow_id == workflow_id)
        .order_by(Execution.created_at.desc())
    )
    return [_to_response(e) for e in result.scalars().all()]


@router.get("/{run_id}", response_model=ExecutionResponse)
async def get_execution(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Get execution details."""
    result = await db.execute(select(Execution).where(Execution.id == run_id))
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return _to_response(execution)


@router.get("/{run_id}/trace")
async def get_execution_trace(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Get detailed trace of all node executions."""
    result = await db.execute(
        select(ExecutionNode)
        .where(ExecutionNode.execution_id == run_id)
        .order_by(ExecutionNode.started_at)
    )
    nodes = result.scalars().all()
    return [
        {
            "id": n.id,
            "node_id": n.node_id,
            "node_name": n.node_name,
            "status": n.status,
            "tokens_in": n.tokens_in,
            "tokens_out": n.tokens_out,
            "cost_usd": n.cost_usd,
            "started_at": str(n.started_at) if n.started_at else None,
            "completed_at": str(n.completed_at) if n.completed_at else None,
            "error": n.error,
        }
        for n in nodes
    ]


@router.post("/{run_id}/cancel", status_code=200)
async def cancel_execution(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Cancel a running execution."""
    result = await db.execute(select(Execution).where(Execution.id == run_id))
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    if execution.status not in ("queued", "running"):
        raise HTTPException(status_code=400, detail="Execution cannot be cancelled")

    execution.status = "cancelled"
    execution.completed_at = datetime.now(timezone.utc)
    await db.flush()
    return {"status": "cancelled"}
