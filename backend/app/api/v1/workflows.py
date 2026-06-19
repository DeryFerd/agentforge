"""Workflow CRUD endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.execution import Execution
from app.models.misc import CostRecord
from app.models.user import User
from app.models.workflow import Workflow

router = APIRouter()


class CreateWorkflowRequest(BaseModel):
    workspace_id: str
    name: str
    description: str | None = None
    dag_json: dict = {}


class UpdateWorkflowRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    dag_json: dict | None = None


class ImportWorkflowRequest(BaseModel):
    workspace_id: str
    name: str | None = None
    dag: dict


class WorkflowResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: str | None
    dag_json: dict | None = None
    version: int
    is_active: bool
    created_at: str
    updated_at: str
    model_config = {"from_attributes": True}


def _to_response(w: Workflow) -> WorkflowResponse:
    return WorkflowResponse(
        id=w.id,
        workspace_id=w.workspace_id,
        name=w.name,
        description=w.description,
        dag_json=w.dag_json,
        version=w.version,
        is_active=w.is_active,
        created_at=str(w.created_at),
        updated_at=str(w.updated_at),
    )


@router.get("", response_model=list[WorkflowResponse])
async def list_workflows(
    workspace_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """List workflows, optionally filtered by workspace."""
    query = select(Workflow).where(Workflow.is_active == True)
    if workspace_id:
        query = query.where(Workflow.workspace_id == workspace_id)
    result = await db.execute(query.order_by(Workflow.updated_at.desc()))
    return [_to_response(w) for w in result.scalars().all()]


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    body: CreateWorkflowRequest,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Create a new workflow."""
    workflow = Workflow(
        workspace_id=body.workspace_id,
        name=body.name,
        description=body.description,
        dag_json=body.dag_json,
        created_by=user.id,
    )
    db.add(workflow)
    await db.flush()
    await db.refresh(workflow)
    return _to_response(workflow)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Get a workflow by ID."""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return _to_response(workflow)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    body: UpdateWorkflowRequest,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Update a workflow."""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if body.name is not None:
        workflow.name = body.name
    if body.description is not None:
        workflow.description = body.description
    if body.dag_json is not None:
        workflow.dag_json = body.dag_json
        workflow.version += 1

    await db.flush()
    await db.refresh(workflow)
    return _to_response(workflow)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Soft-delete a workflow."""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    workflow.is_active = False
    await db.flush()


@router.post("/{workflow_id}/validate")
async def validate_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Validate a workflow's DAG structure."""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    from app.engine.validator import DAGValidator

    validator = DAGValidator(workflow.dag_json)
    return validator.validate()


@router.get("/{workflow_id}/export")
async def export_workflow(
    workflow_id: str,
    format: str = "json",
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Export a workflow as JSON or YAML."""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    export_data = {
        "name": workflow.name,
        "description": workflow.description,
        "dag": workflow.dag_json,
        "version": workflow.version,
        "exported_at": str(workflow.updated_at),
    }

    if format == "yaml":
        import yaml
        from fastapi.responses import PlainTextResponse

        return PlainTextResponse(
            content=yaml.dump(export_data, default_flow_style=False),
            media_type="text/yaml",
            headers={"Content-Disposition": f"attachment; filename={workflow.name}.yaml"},
        )

    return export_data


@router.post("/import", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def import_workflow(
    body: ImportWorkflowRequest,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Import a workflow from a DAG definition."""
    from app.engine.validator import DAGValidator

    validator = DAGValidator(body.dag)
    validation = validator.validate()
    if not validation["valid"]:
        raise HTTPException(
            status_code=400,
            detail={"message": "Invalid DAG", "errors": validation["errors"]},
        )

    workflow = Workflow(
        workspace_id=body.workspace_id,
        name=body.name or "Imported Workflow",
        dag_json=body.dag,
        created_by=user.id,
    )
    db.add(workflow)
    await db.flush()
    await db.refresh(workflow)
    return _to_response(workflow)


@router.get("/dashboard/summary")
async def dashboard_summary(
    workspace_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Get workflow list enriched with execution stats and cost data for the dashboard."""
    query = select(Workflow).where(Workflow.is_active == True)
    if workspace_id:
        query = query.where(Workflow.workspace_id == workspace_id)
    result = await db.execute(query.order_by(Workflow.updated_at.desc()))
    workflows = result.scalars().all()

    wf_ids = [w.id for w in workflows]
    if not wf_ids:
        return {"workflows": []}

    # Execution stats per workflow
    exec_stats = await db.execute(
        select(
            Execution.workflow_id,
            func.count(Execution.id).label("total_runs"),
            func.max(Execution.created_at).label("last_run_at"),
        )
        .where(Execution.workflow_id.in_(wf_ids))
        .group_by(Execution.workflow_id)
    )
    exec_map = {row.workflow_id: {"total_runs": row.total_runs, "last_run_at": str(row.last_run_at)} for row in exec_stats.all()}

    # Last execution status per workflow
    last_status_result = await db.execute(
        select(Execution.workflow_id, Execution.status)
        .where(Execution.workflow_id.in_(wf_ids))
        .order_by(Execution.created_at.desc())
    )
    last_status_map: dict[str, str] = {}
    for row in last_status_result.all():
        if row.workflow_id not in last_status_map:
            last_status_map[row.workflow_id] = row.status

    # Cost per workflow
    cost_stats = await db.execute(
        select(CostRecord.workflow_id, func.sum(CostRecord.cost_usd).label("total_cost"))
        .where(CostRecord.workflow_id.in_(wf_ids))
        .group_by(CostRecord.workflow_id)
    )
    cost_map = {row.workflow_id: round(row.total_cost, 4) for row in cost_stats.all()}

    return {
        "workflows": [
            {
                **_to_response(w).model_dump(),
                "execution_count": exec_map.get(w.id, {}).get("total_runs", 0),
                "last_run_at": exec_map.get(w.id, {}).get("last_run_at"),
                "last_execution_status": last_status_map.get(w.id),
                "total_cost_usd": cost_map.get(w.id, 0.0),
            }
            for w in workflows
        ]
    }
