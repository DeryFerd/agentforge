"""MCP (Model Context Protocol) client — connects to registered MCP servers and calls tools."""

from typing import Any

import structlog
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client

logger = structlog.get_logger()


async def call_mcp_tool(
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any],
    transport: str = "stdio",
    url: str | None = None,
    command: str | None = None,
    args: list[str] | None = None,
) -> Any:
    """Call a tool on an MCP server and return the result.

    Args:
        server_name: Human-readable name of the MCP server
        tool_name: Name of the tool to call
        arguments: Tool arguments as a dict
        transport: "stdio" or "sse"
        url: SSE server URL (for transport="sse")
        command: Command to start stdio server (for transport="stdio")
        args: Command arguments for stdio server

    Returns:
        Tool result (parsed from MCP content blocks)
    """
    if transport == "sse":
        return await _call_sse(url, tool_name, arguments)
    else:
        return await _call_stdio(command, args, tool_name, arguments)


async def _call_stdio(
    command: str | None,
    args: list[str] | None,
    tool_name: str,
    arguments: dict[str, Any],
) -> Any:
    """Call a tool via a stdio MCP server."""
    if not command:
        raise ValueError("MCP stdio transport requires a 'command' parameter")

    server_params = StdioServerParameters(command=command, args=args or [])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return _parse_mcp_result(result)


async def _call_sse(
    url: str | None,
    tool_name: str,
    arguments: dict[str, Any],
) -> Any:
    """Call a tool via an SSE MCP server."""
    if not url:
        raise ValueError("MCP SSE transport requires a 'url' parameter")

    async with sse_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return _parse_mcp_result(result)


def _parse_mcp_result(result: Any) -> Any:
    """Parse MCP CallToolResult into a Python-friendly format."""
    if hasattr(result, "content"):
        # Extract text from content blocks
        texts = []
        for block in result.content:
            if hasattr(block, "text"):
                texts.append(block.text)
            elif hasattr(block, "data"):
                texts.append(block.data)
            else:
                texts.append(str(block))
        return "\n".join(texts) if texts else str(result)
    return str(result)


async def list_mcp_tools(
    transport: str = "stdio",
    url: str | None = None,
    command: str | None = None,
    args: list[str] | None = None,
) -> list[dict[str, Any]]:
    """List all available tools from an MCP server.

    Returns a list of tool descriptions with name, description, and input schema.
    """
    try:
        if transport == "sse":
            async with sse_client(url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    return _format_tool_list(tools)
        else:
            server_params = StdioServerParameters(command=command, args=args or [])
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    return _format_tool_list(tools)
    except Exception as e:
        logger.error("Failed to list MCP tools", error=str(e))
        return []


def _format_tool_list(tools: Any) -> list[dict[str, Any]]:
    """Format MCP tool list into dicts."""
    result = []
    tool_list = tools.tools if hasattr(tools, "tools") else []
    for tool in tool_list:
        result.append({
            "name": tool.name,
            "description": getattr(tool, "description", ""),
            "input_schema": tool.inputSchema if hasattr(tool, "inputSchema") else {},
        })
    return result
