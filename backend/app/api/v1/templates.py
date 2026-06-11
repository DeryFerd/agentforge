"""Agent template registry endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.misc import AgentTemplate

router = APIRouter()


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: str | None
    category: str
    version: str
    is_verified: bool
    download_count: int
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
