"""Cost tracking and budget management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.misc import CostRecord

router = APIRouter()


@router.get("/dashboard")
async def cost_dashboard(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Get cost dashboard summary for a workspace."""
    # Total cost
    total_result = await db.execute(
        select(func.sum(CostRecord.cost_usd)).where(CostRecord.workspace_id == workspace_id)
    )
    total_cost = total_result.scalar() or 0.0

    # Cost by model
    model_result = await db.execute(
        select(CostRecord.model, func.sum(CostRecord.cost_usd))
        .where(CostRecord.workspace_id == workspace_id)
        .group_by(CostRecord.model)
    )
    by_model = {row[0]: row[1] for row in model_result.all()}

    return {
        "workspace_id": workspace_id,
        "total_cost_usd": round(total_cost, 4),
        "cost_by_model": by_model,
    }


@router.get("/workflows/{workflow_id}")
async def workflow_costs(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Get cost breakdown for a specific workflow."""
    result = await db.execute(
        select(func.sum(CostRecord.cost_usd)).where(CostRecord.workflow_id == workflow_id)
    )
    total = result.scalar() or 0.0
    return {"workflow_id": workflow_id, "total_cost_usd": round(total, 4)}


@router.get("/executions/{run_id}")
async def execution_costs(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Get cost breakdown for a specific execution."""
    result = await db.execute(
        select(CostRecord).where(CostRecord.execution_id == run_id)
    )
    records = result.scalars().all()
    total = sum(r.cost_usd for r in records)
    return {
        "execution_id": run_id,
        "total_cost_usd": round(total, 4),
        "breakdown": [
            {"node_id": r.node_id, "model": r.model, "cost_usd": r.cost_usd}
            for r in records
        ],
    }
