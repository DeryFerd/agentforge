"""Budget enforcement — pause execution when cost limits are exceeded."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution import Execution
from app.models.misc import CostRecord
from app.models.workflow import Workflow

import structlog

logger = structlog.get_logger()


class BudgetExceededError(Exception):
    """Raised when a budget limit is exceeded."""

    def __init__(self, limit_type: str, limit_value: float, current_value: float):
        self.limit_type = limit_type
        self.limit_value = limit_value
        self.current_value = current_value
        super().__init__(
            f"Budget exceeded: {limit_type} limit ${limit_value:.4f}, current ${current_value:.4f}"
        )


async def get_workspace_cost(workspace_id: str, db: AsyncSession) -> float:
    """Get total cost for a workspace (all time)."""
    result = await db.execute(
        select(func.sum(CostRecord.cost_usd)).where(CostRecord.workspace_id == workspace_id)
    )
    return result.scalar() or 0.0


async def get_workflow_cost(workflow_id: str, db: AsyncSession) -> float:
    """Get total cost for a specific workflow."""
    result = await db.execute(
        select(func.sum(CostRecord.cost_usd)).where(CostRecord.workflow_id == workflow_id)
    )
    return result.scalar() or 0.0


async def get_execution_cost(execution_id: str, db: AsyncSession) -> float:
    """Get total cost for a specific execution run."""
    result = await db.execute(
        select(func.sum(CostRecord.cost_usd)).where(CostRecord.execution_id == execution_id)
    )
    return result.scalar() or 0.0


async def check_budget(
    workflow_id: str,
    workspace_id: str,
    db: AsyncSession,
    per_run_limit: float | None = None,
    per_workflow_limit: float | None = None,
    per_workspace_limit: float | None = None,
) -> dict:
    """Check all budget limits and return status.

    Returns dict with:
        - allowed: bool
        - warnings: list of warning messages
        - errors: list of budget violation messages
    """
    warnings = []
    errors = []

    # Per-run limit is checked during execution (node-by-node)
    # Here we check workflow and workspace level budgets

    if per_workflow_limit is not None:
        wf_cost = await get_workflow_cost(workflow_id, db)
        if wf_cost >= per_workflow_limit:
            errors.append(
                f"Workflow budget exceeded: ${wf_cost:.4f} / ${per_workflow_limit:.4f}"
            )
        elif wf_cost >= per_workflow_limit * 0.8:
            warnings.append(
                f"Workflow budget warning: ${wf_cost:.4f} / ${per_workflow_limit:.4f} (80%)"
            )

    if per_workspace_limit is not None:
        ws_cost = await get_workspace_cost(workspace_id, db)
        if ws_cost >= per_workspace_limit:
            errors.append(
                f"Workspace budget exceeded: ${ws_cost:.4f} / ${per_workspace_limit:.4f}"
            )
        elif ws_cost >= per_workspace_limit * 0.8:
            warnings.append(
                f"Workspace budget warning: ${ws_cost:.4f} / ${per_workspace_limit:.4f} (80%)"
            )

    return {
        "allowed": len(errors) == 0,
        "warnings": warnings,
        "errors": errors,
    }


async def check_node_budget(
    execution_id: str,
    db: AsyncSession,
    per_run_limit: float | None = None,
) -> bool:
    """Check if adding another node would exceed per-run budget.

    Call this before executing each node. Returns True if within budget.
    """
    if per_run_limit is None:
        return True

    current_cost = await get_execution_cost(execution_id, db)
    if current_cost >= per_run_limit:
        logger.warning(
            "Per-run budget exceeded",
            execution_id=execution_id,
            current_cost=current_cost,
            limit=per_run_limit,
        )
        return False
    return True
