"""Seed built-in MCP servers on first startup."""

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.misc import MCPServer
from app.models.user import User
from app.models.workspace import Workspace

logger = structlog.get_logger()

MCP_SERVERS = [
    {
        "name": "filesystem",
        "transport": "stdio",
        "command": "npx",
        "args_json": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        "description": "Read, write, and search local files in /tmp directory",
    },
    {
        "name": "web-search",
        "transport": "stdio",
        "command": "npx",
        "args_json": ["-y", "@modelcontextprotocol/server-brave-search"],
        "description": "Search the web using Brave Search API",
    },
    {
        "name": "postgres",
        "transport": "stdio",
        "command": "npx",
        "args_json": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://agentforge:agentforge@localhost:5432/agentforge"],
        "description": "Query the AgentForge PostgreSQL database",
    },
]


async def seed_mcp_servers(db: AsyncSession) -> None:
    """Insert built-in MCP servers if none exist. Idempotent."""
    count = await db.scalar(select(func.count()).select_from(MCPServer))
    if count and count > 0:
        logger.info("MCP servers already seeded", count=count)
        return

    # Get default workspace (create one if needed)
    workspace = await db.scalar(select(Workspace).limit(1))
    if not workspace:
        # Need a system user as workspace owner
        system_user = await db.scalar(select(User).where(User.email == "system@agentforge.local"))
        if not system_user:
            system_user = User(
                email="system@agentforge.local",
                full_name="AgentForge System",
                password_hash="system",
            )
            db.add(system_user)
            await db.flush()
        workspace = Workspace(name="Default Workspace", owner_id=system_user.id)
        db.add(workspace)
        await db.flush()
        logger.info("Created default workspace for MCP servers")

    for s in MCP_SERVERS:
        server = MCPServer(
            workspace_id=workspace.id,
            name=s["name"],
            transport=s["transport"],
            command=s["command"],
            args_json=s["args_json"],
            health_status="unknown",
        )
        db.add(server)

    await db.flush()
    logger.info("Seeded MCP servers", count=len(MCP_SERVERS))
