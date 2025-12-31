from dotenv import load_dotenv
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv(override=True)
brave_api_key = os.getenv("BRAVE_API_KEY")

# Validate that BRAVE_API_KEY is set
if not brave_api_key:
    raise ValueError(
        "BRAVE_API_KEY environment variable is not set. "
        "Please set it in your .env file or as an environment variable. "
        "Get your API key from: https://api.search.brave.com/"
    )

brave_env = {"BRAVE_API_KEY": brave_api_key}

working_directory = os.getcwd()
print(f"Working directory: {working_directory}")

drafter_mcp_server_params = [
    {
        "command": "python",
        "args": ["mcp_servers/draft_server.py"],
        "working_directory": "/app"
    }
]

researcher_mcp_server_params = [
    {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-brave-search"], "env": brave_env}
		
]
'''
researcher_mcp_server_params = [
{
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "BRAVE_MCP_TRANSPORT",
        "-e",
        "BRAVE_API_KEY",
        "mcp/brave-search"
      ],
      "env": {
        "BRAVE_MCP_TRANSPORT": "stdio",
        "BRAVE_API_KEY": brave_api_key
      }
}
]
'''