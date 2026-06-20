"""Agent template registry endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.misc import AgentTemplate
from app.models.user import User

router = APIRouter()


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: str | None
    category: str
    version: str
    is_verified: bool
    download_count: int
    system_prompt: str | None = None
    model_config_json: dict | None = None
    model_config = {"from_attributes": True}


class CreateTemplateRequest(BaseModel):
    name: str
    description: str | None = None
    category: str = "general"
    system_prompt: str
    model_config_json: dict = {}
    input_schema: dict | None = None
    output_schema: dict | None = None


@router.get("", response_model=list[TemplateResponse])
async def list_templates(
    category: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List available agent templates."""
    query = select(AgentTemplate)
    if category:
        query = query.where(AgentTemplate.category == category)
    if search:
        query = query.where(AgentTemplate.name.ilike(f"%{search}%"))
    result = await db.execute(query.order_by(AgentTemplate.download_count.desc()))
    return result.scalars().all()


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    body: CreateTemplateRequest,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Create a new agent template."""
    template = AgentTemplate(
        name=body.name,
        description=body.description,
        category=body.category,
        system_prompt=body.system_prompt,
        model_config_json=body.model_config_json,
        input_schema=body.input_schema,
        output_schema=body.output_schema,
        author_id=user.id,
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get template details."""
    result = await db.execute(select(AgentTemplate).where(AgentTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/{template_id}/install")
async def install_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Install a template — creates a new workflow with a pre-configured agent node."""
    result = await db.execute(select(AgentTemplate).where(AgentTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Build a DAG with Input → Agent (from template) → Output
    model_cfg = template.model_config_json or {"provider": "openai", "model_id": "gpt-oss:20b-cloud", "temperature": 0.3}
    agent_config = {
        "system_prompt": template.system_prompt,
        "model": model_cfg,
        "tools": [],
    }

    dag = {
        "nodes": [
            {
                "id": "input_template",
                "type": "input",
                "position": {"x": 100, "y": 200},
                "config": {},
            },
            {
                "id": f"agent_{template_id[:8]}",
                "type": "agent",
                "position": {"x": 400, "y": 200},
                "config": agent_config,
            },
            {
                "id": "output_template",
                "type": "output",
                "position": {"x": 700, "y": 200},
                "config": {},
            },
        ],
        "edges": [
            {"id": "e1", "source": "input_template", "target": f"agent_{template_id[:8]}"},
            {"id": "e2", "source": f"agent_{template_id[:8]}", "target": "output_template"},
        ],
    }

    # Get user's workspace (or use first available)
    from app.models.workflow import Workflow
    from app.models.workspace import Workspace
    workspace = await db.scalar(select(Workspace).limit(1))
    if not workspace:
        raise HTTPException(status_code=400, detail="No workspace found. Create one first.")

    workflow = Workflow(
        workspace_id=workspace.id,
        name=f"{template.name} Workflow",
        description=template.description or f"Created from {template.name} template",
        dag_json=dag,
        created_by=user.id,
    )
    db.add(workflow)

    # Increment download count
    template.download_count = (template.download_count or 0) + 1

    await db.flush()
    await db.refresh(workflow)

    return {"workflow_id": workflow.id, "workflow_name": workflow.name}
