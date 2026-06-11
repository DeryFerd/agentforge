"""Workspace management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_current_user_id, log_audit, require_admin
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember

router = APIRouter()


class CreateWorkspaceRequest(BaseModel):
    name: str


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    owner_id: str
    model_config = {"from_attributes": True}


class InviteMemberRequest(BaseModel):
    user_id: str
    role: str = "viewer"


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """List all workspaces the current user belongs to."""
    result = await db.execute(
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
    )
    return result.scalars().all()


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    body: CreateWorkspaceRequest,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Create a new workspace. The creator becomes the owner."""
    workspace = Workspace(name=body.name, owner_id=user.id)
    db.add(workspace)
    await db.flush()

    # Add creator as owner member
    member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner")
    db.add(member)
    await db.flush()
    await db.refresh(workspace)
    return workspace


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Get workspace details."""
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.post("/{workspace_id}/members", status_code=status.HTTP_201_CREATED)
async def invite_member(
    workspace_id: str,
    body: InviteMemberRequest,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Invite a user to the workspace with a specific role."""
    # Check that the inviter is at least admin
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    inviter = result.scalar_one_or_none()
    if not inviter or inviter.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owners and admins can invite members")
    member = WorkspaceMember(workspace_id=workspace_id, user_id=body.user_id, role=body.role)
    db.add(member)
    await log_audit(db, workspace_id, user.id, "invite_member", "workspace_member", body.user_id, {"role": body.role})
    await db.flush()
    return {"message": "Member invited", "role": body.role}


@router.get("/{workspace_id}/members")
async def list_members(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """List all members of a workspace."""
    result = await db.execute(
        select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)
    )
    members = result.scalars().all()
    return [{"user_id": m.user_id, "role": m.role, "joined_at": str(m.joined_at)} for m in members]
