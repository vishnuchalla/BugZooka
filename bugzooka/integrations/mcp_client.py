import json
import logging
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)

mcp_client = None
mcp_tools = []

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
        with open(mcp_config_path, 'r') as f:
            config = json.load(f)

        mcp_client = MultiServerMCPClient(config['mcp_servers'])
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