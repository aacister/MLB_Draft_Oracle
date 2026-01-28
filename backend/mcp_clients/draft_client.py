"""
Simplified draft_client.py using run-mcp-servers-with-aws-lambda package.
Replace your existing draft_client.py with this version.
"""
from typing import List
import json
import os
import logging
from agents import FunctionTool

logger = logging.getLogger(__name__)

# Detect if running in Lambda
IS_LAMBDA = os.path.exists("/var/task") or os.getenv("WORKER_LAMBDA_FUNCTION_NAME")

if IS_LAMBDA:
    # Use the package's Lambda MCP client
    from backend.mcp_clients.lambda_mcp_client import get_draft_mcp_client
    
    logger.info("Using Lambda-based MCP client for draft server")
    draft_client = get_draft_mcp_client()
else:
    # Use stdio for local development (unchanged)
    import mcp
    from mcp.client.stdio import stdio_client
    from mcp import StdioServerParameters
    
    logger.info("Using stdio-based MCP client for draft server (local dev)")
    
    def get_drafter_params():
        working_dir = os.getcwd()
        python_cmd = "python"
        
        env = {
            "PYTHONPATH": working_dir,
            "PATH": os.environ.get("PATH", ""),
            "DB_URL": os.getenv("DB_URL", ""),  # ← Changed
            "AWS_REGION": os.getenv("AWS_REGION", "us-east-2"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
            "DEPLOYMENT_ENVIRONMENT": "DEV",
        }
        
        env = {k: v for k, v in env.items() if v}
        
        return StdioServerParameters(
            command=python_cmd,
            args=[f"{working_dir}/backend/mcp_servers/draft_server.py"],
            env=env
        )
    
    params = get_drafter_params()


async def list_draft_tools():
    """List available draft tools"""
    if IS_LAMBDA:
        # The package handles all the protocol details
        return await draft_client.list_tools()
    else:
        async with stdio_client(params) as streams:
            async with mcp.ClientSession(*streams) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                return tools_result.tools


async def call_draft_tool(tool_name, tool_args):
    """Call a draft tool"""
    logger.info(f"Calling draft tool: {tool_name}")
    
    if IS_LAMBDA:
        # The package handles serialization/deserialization
        result = await draft_client.call_tool(tool_name, tool_args)
        logger.info(f"Draft Tool {tool_name} Result: {result}")
        return result
    else:
        async with stdio_client(params) as streams:
            async with mcp.ClientSession(*streams) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, tool_args)
                logger.info(f"Draft Tool {tool_name} Result: {result}")
                return result


async def read_team_roster_resource(id, team_name):
    """Read team roster resource"""
    uri = f"draft://team_roster/{id}/{team_name}"
    
    if IS_LAMBDA:
        # The package handles resource reading
        return await draft_client.read_resource(uri)
    else:
        async with stdio_client(params) as streams:
            async with mcp.ClientSession(*streams) as session:
                await session.initialize()
                result = await session.read_resource(uri)
                return result.contents[0].text


async def read_player_pool_resource(id):
    """Read player pool resource"""
    uri = f"draft://player_pool/{id.lower()}"
    
    if IS_LAMBDA:
        return await draft_client.read_resource(uri)
    else:
        async with stdio_client(params) as streams:
            async with mcp.ClientSession(*streams) as session:
                await session.initialize()
                result = await session.read_resource(uri)
                return result.contents[0].text


async def read_draft_player_pool_available_resource(id):
    """Read available player pool resource"""
    uri = f"draft://player_pool/{id.lower()}/available"
    
    if IS_LAMBDA:
        return await draft_client.read_resource(uri)
    else:
        async with stdio_client(params) as streams:
            async with mcp.ClientSession(*streams) as session:
                await session.initialize()
                result = await session.read_resource(uri)
                return result.contents[0].text


async def read_draft_order_resource(id, round):
    """Read draft order resource"""
    uri = f"draft://draft_order/{id.lower()}/round/{round}"
    
    if IS_LAMBDA:
        return await draft_client.read_resource(uri)
    else:
        async with stdio_client(params) as streams:
            async with mcp.ClientSession(*streams) as session:
                await session.initialize()
                result = await session.read_resource(uri)
                return result.contents[0].text


async def read_draft_history_resource(id):
    """Read draft history resource"""
    uri = f"draft://history/{id.lower()}"
    
    if IS_LAMBDA:
        return await draft_client.read_resource(uri)
    else:
        async with stdio_client(params) as streams:
            async with mcp.ClientSession(*streams) as session:
                await session.initialize()
                result = await session.read_resource(uri)
                return result.contents[0].text


def set_additional_properties_false(schema, defs=None, visited=None):
    """Helper function to set additionalProperties to false in JSON schemas"""
    if visited is None:
        visited = set()
    if defs is None and isinstance(schema, dict):
        defs = schema.get('$defs', {})
    if isinstance(schema, dict):
        schema_id = id(schema)
        if schema_id in visited:
            return schema
        visited.add(schema_id)
        if schema.get("type") == "object":
            schema["additionalProperties"] = False
            if "properties" in schema:
                for key, prop in list(schema["properties"].items()):
                    if isinstance(prop, dict) and "$ref" in prop:
                        ref_val = prop["$ref"]
                        schema["properties"][key] = {"$ref": ref_val}
                        set_additional_properties_false(schema["properties"][key], defs, visited)
                    else:
                        set_additional_properties_false(prop, defs, visited)
                required_keys = list(schema["properties"].keys())
                for key, prop in schema["properties"].items():
                    if (
                        isinstance(prop, dict)
                        and prop.get("type") == "object"
                        and "additionalProperties" in prop
                    ):
                        if key in required_keys:
                            required_keys.remove(key)
                schema["required"] = required_keys
        elif schema.get("type") == "array" and "items" in schema:
            set_additional_properties_false(schema["items"], defs, visited)
        if "$ref" in schema and defs is not None:
            ref = schema["$ref"]
            if ref.startswith("#/$defs/"):
                def_name = ref.split("#/$defs/")[-1]
                if def_name in defs:
                    set_additional_properties_false(defs[def_name], defs, visited)
    if defs is not None:
        for def_schema in defs.values():
            set_additional_properties_false(def_schema, defs, visited)
    return schema


async def get_draft_tools():
    """Get draft tools as OpenAI-compatible FunctionTools"""
    openai_tools = []
    tools = await list_draft_tools()
    
    for tool in tools:
        # Handle both formats (package normalizes this)
        if isinstance(tool, dict):
            tool_name = tool.get('name')
            tool_description = tool.get('description', '')
            schema = tool.get('inputSchema', {})
        else:
            tool_name = tool.name
            tool_description = tool.description
            schema = tool.inputSchema
        
        schema = set_additional_properties_false(schema)
        
        openai_tool = FunctionTool(
            name=tool_name,
            description=tool_description,
            params_json_schema=schema,
            on_invoke_tool=lambda ctx, args, toolname=tool_name: call_draft_tool(toolname, json.loads(args))
        )
        openai_tools.append(openai_tool)
    
    return openai_tools