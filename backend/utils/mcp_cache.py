"""
Global MCP server cache for Lambda
"""
import logging
from contextlib import AsyncExitStack
from agents.mcp import MCPServerStdio
from backend.config.mcp_params import drafter_mcp_server_params, researcher_mcp_server_params

logger = logging.getLogger(__name__)

# Global cache (survives across warm Lambda invocations)
_mcp_stack = None
_drafter_servers = None
_researcher_servers = None

async def get_cached_mcp_servers():
    """
    Get or create cached MCP servers.
    Reuses servers across Lambda invocations for faster performance.
    """
    global _mcp_stack, _drafter_servers, _researcher_servers
    
    # If already initialized, return cached servers
    if _drafter_servers is not None and _researcher_servers is not None:
        logger.info("Using cached MCP servers (warm start)")
        return _drafter_servers, _researcher_servers
    
    # Cold start - initialize servers
    logger.info("Initializing MCP servers (cold start)")
    _mcp_stack = AsyncExitStack()
    
    # Initialize drafter servers
    _drafter_servers = []
    for i, params in enumerate(drafter_mcp_server_params):
        try:
            server = await _mcp_stack.enter_async_context(MCPServerStdio(params=params))
            _drafter_servers.append(server)
            logger.info(f"✓ Drafter MCP server {i+1} initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize drafter MCP server {i+1}: {e}")
            raise
    
    # Initialize researcher servers
    _researcher_servers = []
    for i, params in enumerate(researcher_mcp_server_params):
        try:
            server = await _mcp_stack.enter_async_context(MCPServerStdio(params=params))
            _researcher_servers.append(server)
            logger.info(f"✓ Researcher MCP server {i+1} initialized")
        except Exception as e:
            logger.error(f"✗ Failed to initialize researcher MCP server {i+1}: {e}")
            raise
    
    logger.info("All MCP servers initialized and cached")
    return _drafter_servers, _researcher_servers


async def cleanup_mcp_servers():
    """Cleanup MCP servers (call on Lambda shutdown if needed)"""
    global _mcp_stack, _drafter_servers, _researcher_servers
    
    if _mcp_stack:
        await _mcp_stack.aclose()
        _mcp_stack = None
        _drafter_servers = None
        _researcher_servers = None
        logger.info("MCP servers cleaned up")