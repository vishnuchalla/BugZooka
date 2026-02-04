import json
import logging
from typing import Any, Optional

from langchain_mcp_adapters.client import MultiServerMCPClient

from bugzooka.core.utils import make_response

logger = logging.getLogger(__name__)

mcp_client = None
mcp_tools: list = []


async def initialize_global_resources_async(mcp_config_path: str = "mcp_config.json"):
    """
    Initializes the MCP client and retrieves tools.
    This version includes graceful handling for a missing mcp_config.json file.
    """
    global mcp_client, mcp_tools
    # Initialize the MCP client from a config file.
    if mcp_client is not None:
        return

    try:
        with open(mcp_config_path, "r") as f:
            config = json.load(f)

        mcp_client = MultiServerMCPClient(config["mcp_servers"])
        mcp_tools = await mcp_client.get_tools()
        logger.info(f"MCP configuration loaded and {len(mcp_tools)} tools retrieved.")

    except FileNotFoundError:
        logger.warning(
            f"MCP configuration file not found at {mcp_config_path}. Running without external tools."
        )
        mcp_tools = []
        # Create a dummy client to avoid crashing, though it won't be used.
        mcp_client = MultiServerMCPClient({})
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in MCP configuration file: {e}")
        raise
    except Exception as e:
        logger.error(f"Error initializing MCP tools: {e}", exc_info=True)
        raise


def get_mcp_tool(tool_name: str) -> Optional[Any]:
    """
    Look up an MCP tool by name.

    :param tool_name: Name of the tool to find
    :return: The tool object if found, None otherwise
    """
    for tool in mcp_tools:
        if tool.name == tool_name:
            return tool
    return None


def get_available_tool_names() -> list[str]:
    """
    Get list of all available MCP tool names.

    :return: List of tool names
    """
    return [t.name for t in mcp_tools]


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
