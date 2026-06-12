"""API key management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.api_key import ApiKey, generate_api_key
from app.models.user import User

router = APIRouter()


class CreateApiKeyRequest(BaseModel):
    workspace_id: str
    name: str


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    is_active: bool
    created_at: str
    last_used_at: str | None
    model_config = {"from_attributes": True}


class CreateApiKeyResult(BaseModel):
    id: str
    name: str
    key: str  # Only shown once on creation
    key_prefix: str


@router.post("", response_model=CreateApiKeyResult, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: CreateApiKeyRequest,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Generate a new API key. The full key is only shown once."""
    full_key, prefix, key_hash = generate_api_key()

    api_key = ApiKey(
        workspace_id=body.workspace_id,
        name=body.name,
        key_prefix=prefix,
        key_hash=key_hash,
        created_by=user.id,
    )
    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)

    return CreateApiKeyResult(
        id=api_key.id,
        name=api_key.name,
        key=full_key,
        key_prefix=prefix,
    )


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """List all API keys for a workspace (shows prefix only, not full key)."""
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.workspace_id == workspace_id)
        .order_by(ApiKey.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Revoke (deactivate) an API key."""
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    api_key.is_active = False
    await db.flush()


@router.post("/{key_id}/rotate", response_model=CreateApiKeyResult)
async def rotate_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Rotate an API key: revoke old, generate new with same name/workspace."""
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    old_key = result.scalar_one_or_none()
    if not old_key:
        raise HTTPException(status_code=404, detail="API key not found")

    # Revoke old
    old_key.is_active = False
    await db.flush()

    # Generate new
    full_key, prefix, key_hash = generate_api_key()
    new_key = ApiKey(
        workspace_id=old_key.workspace_id,
        name=old_key.name,
        key_prefix=prefix,
        key_hash=key_hash,
        created_by=user.id,
    )
    db.add(new_key)
    await db.flush()
    await db.refresh(new_key)

    return CreateApiKeyResult(
        id=new_key.id,
        name=new_key.name,
        key=full_key,
        key_prefix=prefix,
    )
