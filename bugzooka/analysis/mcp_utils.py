"""
Shared utilities for MCP-based analysis tools.
Provides common functionality for initializing MCP client and looking up tools.
"""
import logging
from typing import Any, Optional

from bugzooka.integrations.mcp_client import initialize_global_resources_async
import bugzooka.integrations.mcp_client as mcp_module
from bugzooka.analysis.utils import make_response


logger = logging.getLogger(__name__)


async def ensure_mcp_initialized() -> None:
    """
    Ensure the MCP client is initialized.
    Initializes the client if it hasn't been initialized yet.
    """
    if mcp_module.mcp_client is None:
        await initialize_global_resources_async()


def get_mcp_tool(tool_name: str) -> Optional[Any]:
    """
    Look up an MCP tool by name.

    :param tool_name: Name of the tool to find
    :return: The tool object if found, None otherwise
    """
    for tool in mcp_module.mcp_tools:
        if tool.name == tool_name:
            return tool
    return None


def get_available_tool_names() -> list[str]:
    """
    Get list of all available MCP tool names.

    :return: List of tool names
    """
    return [t.name for t in mcp_module.mcp_tools]


async def invoke_mcp_tool(tool: Any, args: dict) -> str:
    """
    Invoke an MCP tool with the given arguments.

    :param tool: The MCP tool object
    :param args: Arguments to pass to the tool
    :return: Tool result as string
    """
    if hasattr(tool, "ainvoke"):
        result = await tool.ainvoke(args)
    else:
        result = tool.invoke(args)

    if not isinstance(result, str):
        result = str(result)

    return result


def tool_not_found_error(tool_name: str) -> dict[str, Any]:
    """
    Create a standardized error response for when an MCP tool is not found.

    :param tool_name: Name of the tool that wasn't found
    :return: Error response dictionary
    """
    available = get_available_tool_names()
    error_msg = (
        f"MCP tool '{tool_name}' not found. Is the MCP server configured and running?"
    )
    logger.error(error_msg)
    logger.info("Available tools: %s", available)
    return make_response(success=False, message=error_msg)
