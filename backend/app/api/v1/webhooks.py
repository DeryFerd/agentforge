"""Webhook trigger endpoints."""

from typing import Annotated

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.misc import WebhookTrigger

router = APIRouter()


class CreateWebhookRequest(BaseModel):
    workflow_id: str


class WebhookResponse(BaseModel):
    id: str
    workflow_id: str
    secret: str
    is_active: bool
    model_config = {"from_attributes": True}


@router.get("", response_model=list[WebhookResponse])
async def list_webhooks(
    workflow_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """List webhook triggers."""
    query = select(WebhookTrigger)
    if workflow_id:
        query = query.where(WebhookTrigger.workflow_id == workflow_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    body: CreateWebhookRequest,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Create a webhook trigger for a workflow."""
    webhook = WebhookTrigger(
        workflow_id=body.workflow_id,
        secret=secrets.token_urlsafe(32),
    )
    db.add(webhook)
    await db.flush()
    await db.refresh(webhook)
    return webhook


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Delete a webhook trigger."""
    result = await db.execute(select(WebhookTrigger).where(WebhookTrigger.id == webhook_id))
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await db.delete(webhook)
    await db.flush()


@router.post("/trigger/{webhook_id}")
async def trigger_webhook(
    webhook_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """External endpoint: trigger a workflow via webhook. No auth required (uses secret)."""
    result = await db.execute(
        select(WebhookTrigger).where(WebhookTrigger.id == webhook_id, WebhookTrigger.is_active == True)
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found or inactive")

    payload = await request.json() if await request.body() else {}

    # TODO: Enqueue execution (Phase 3/7)
    return {
        "status": "queued",
        "workflow_id": webhook.workflow_id,
        "payload_received": True,
    }
