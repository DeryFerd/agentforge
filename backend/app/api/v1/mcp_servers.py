"""MCP server management endpoints."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.misc import MCPServer

router = APIRouter()


class RegisterMCPServerRequest(BaseModel):
    workspace_id: str
    name: str
    transport: str = "stdio"
    url: str | None = None
    command: str | None = None
    args_json: list | None = None
    auth_config: dict | None = None


class MCPServerResponse(BaseModel):
    id: str
    name: str
    transport: str
    url: str | None = None
    command: str | None = None
    health_status: str
    last_check_at: str | None = None
    model_config = {"from_attributes": True}


@router.get("", response_model=list[MCPServerResponse])
async def list_mcp_servers(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """List registered MCP servers for a workspace."""
    result = await db.execute(
        select(MCPServer).where(MCPServer.workspace_id == workspace_id)
    )
    return result.scalars().all()


@router.post("", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def register_mcp_server(
    body: RegisterMCPServerRequest,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Register a new MCP server."""
    server = MCPServer(
        workspace_id=body.workspace_id,
        name=body.name,
        transport=body.transport,
        url=body.url,
        command=body.command,
        args_json=body.args_json,
        auth_config=body.auth_config,
    )
    db.add(server)
    await db.flush()
    await db.refresh(server)
    return server


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deregister_mcp_server(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Remove a registered MCP server."""
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    await db.delete(server)
    await db.flush()


@router.get("/{server_id}/health")
async def get_mcp_server_health(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Check health status of an MCP server by attempting a connection."""
    from datetime import datetime, timezone

    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")

    health = "unknown"
    detail = ""

    if server.transport == "sse" and server.url:
        # Try to connect to SSE endpoint
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(server.url)
                if resp.status_code < 500:
                    health = "healthy"
                    detail = f"HTTP {resp.status_code}"
                else:
                    health = "unhealthy"
                    detail = f"HTTP {resp.status_code}"
        except Exception as e:
            health = "unreachable"
            detail = str(e)[:100]
    elif server.transport == "stdio" and server.command:
        # For stdio, check if the command exists on the system
        import shutil
        import sys
        cmd = server.command.split()[0] if server.command else ""
        # On Windows, also check .cmd/.bat extensions
        found = shutil.which(cmd)
        if not found and sys.platform == "win32":
            for ext in [".cmd", ".bat", ".exe"]:
                if shutil.which(cmd + ext):
                    found = cmd + ext
                    break
        if found:
            health = "configured"
            detail = f"Command '{cmd}' found ({found})"
        else:
            health = "not_installed"
            detail = f"Command '{cmd}' not found on system"

    # Update the stored health status
    server.health_status = health
    server.last_check_at = datetime.now(timezone.utc)
    await db.flush()
    await db.commit()

    return {
        "server_id": server.id,
        "name": server.name,
        "status": health,
        "detail": detail,
        "transport": server.transport,
    }
"""MCP server management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.misc import MCPServer

router = APIRouter()


class RegisterMCPServerRequest(BaseModel):
    workspace_id: str
    name: str
    transport: str = "stdio"
    url: str | None = None
    command: str | None = None
    args_json: list | None = None
    auth_config: dict | None = None


class MCPServerResponse(BaseModel):
    id: str
    name: str
    transport: str
    health_status: str
    model_config = {"from_attributes": True}


@router.get("", response_model=list[MCPServerResponse])
async def list_mcp_servers(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """List registered MCP servers for a workspace."""
    result = await db.execute(
        select(MCPServer).where(MCPServer.workspace_id == workspace_id)
    )
    return result.scalars().all()


@router.post("", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def register_mcp_server(
    body: RegisterMCPServerRequest,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Register a new MCP server."""
    server = MCPServer(
        workspace_id=body.workspace_id,
        name=body.name,
        transport=body.transport,
        url=body.url,
        command=body.command,
        args_json=body.args_json,
        auth_config=body.auth_config,
    )
    db.add(server)
    await db.flush()
    await db.refresh(server)
    return server


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deregister_mcp_server(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Remove a registered MCP server."""
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    await db.delete(server)
    await db.flush()


@router.get("/{server_id}/health")
async def get_mcp_server_health(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    user: Annotated[User, Depends(get_current_user)] = ...,
):
    """Check health status of an MCP server."""
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    # TODO: Actually ping the MCP server (Phase 6)
    return {"server_id": server.id, "status": server.health_status}
