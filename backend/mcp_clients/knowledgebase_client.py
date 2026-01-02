from typing import List
import mcp
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters
from agents import FunctionTool
import json

params = StdioServerParameters(
    command="python",
    args=["mcp_servers/knowledgebase_server.py"],
    env=None
)


async def list_knowledgebase_tools():
    """List all available tools from the knowledge base MCP server."""
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            return tools_result.tools


async def call_knowledgebase_tool(tool_name, tool_args):
    """Call a specific tool from the knowledge base MCP server."""
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, tool_args)
            print(f"Knowledge Base Tool {tool_name} Result: {result}")
            return result


def set_additional_properties_false(schema, defs=None, visited=None):
    """Helper function to set additionalProperties to false in JSON schemas."""
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


async def get_knowledgebase_tools():
    """Get knowledge base tools as OpenAI-compatible FunctionTools."""
    openai_tools = []
    for tool in await list_knowledgebase_tools():
        schema = set_additional_properties_false(tool.inputSchema)
        openai_tool = FunctionTool(
            name=tool.name,
            description=tool.description,
            params_json_schema=schema,
            on_invoke_tool=lambda ctx, args, toolname=tool.name: call_knowledgebase_tool(toolname, json.loads(args))
        )
        openai_tools.append(openai_tool)
    return openai_tools