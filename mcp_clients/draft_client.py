from typing import List
import mcp
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters
from agents import FunctionTool
import json




#params = StdioServerParameters(command="uv", args=["run", "draft_server.py"], env=None)
params = StdioServerParameters(command="uv", args=["run", "mcp_servers/draft_server.py"])


async def list_draft_tools():
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            return tools_result.tools
        
async def call_draft_tool(tool_name, tool_args):
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, tool_args)
            print(f"Draft Tool {tool_name}Result: {result}")
            return result
        
async def read_team_roster_resource(id, team_name):
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            result = await session.read_resource(f"draft://team_roster/{id}/{team_name}")
            return result.contents[0].text
        
async def read_player_pool_resource(id):
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            result = await session.read_resource(f"draft://player_pool/{id.lower()}")
            return result.contents[0].text

async def read_draft_player_pool_available_resource(id):
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            result = await session.read_resource(f"draft://player_pool/{id.lower()}/available")
            return result.contents[0].text
        
async def read_draft_order_resource(id, round):
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            result = await session.read_resource(f"draft://draft_order{id.lower()}/round/{round}")
            return result.contents[9].text
        
async def read_draft_history_resource(id):
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            result = await session.read_resource(f"draft://history/{id.lower()}")
            return result.contents[0].text

def set_additional_properties_false(schema, defs=None, visited=None):
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
                    # If property is a $ref, remove all other keys except $ref
                    if isinstance(prop, dict) and "$ref" in prop:
                        ref_val = prop["$ref"]
                        schema["properties"][key] = {"$ref": ref_val}
                        set_additional_properties_false(schema["properties"][key], defs, visited)
                    else:
                        set_additional_properties_false(prop, defs, visited)
                # After all property processing, set required to match properties, but remove dynamic dicts
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
        # Handle $ref
        if "$ref" in schema and defs is not None:
            ref = schema["$ref"]
            if ref.startswith("#/$defs/"):
                def_name = ref.split("#/$defs/")[-1]
                if def_name in defs:
                    set_additional_properties_false(defs[def_name], defs, visited)
    # Also process $defs at the root
    if defs is not None:
        for def_schema in defs.values():
            set_additional_properties_false(def_schema, defs, visited)
    return schema

async def get_draft_tools():
    openai_tools = []
    for tool in await list_draft_tools():
        schema = set_additional_properties_false(tool.inputSchema)
        openai_tool = FunctionTool(
            name=tool.name,
            description=tool.description,
            params_json_schema=schema,
            on_invoke_tool=lambda ctx, args, toolname=tool.name: call_draft_tool(toolname, json.loads(args))
        )
        openai_tools.append(openai_tool)
    return openai_tools

