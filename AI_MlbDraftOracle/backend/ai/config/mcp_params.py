from dotenv import load_dotenv
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv(override=True)
#{"command": "uvx", "args": ["mcp-server-fetch"]},
#{"command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"]},
brave_env = {"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY")}

working_directory = os.getcwd()
print(f"Working directory: {working_directory}")
server_directory = f"{working_directory}\\ai\\server"

researcher_mcp_server_params = [
    {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-brave-search"], "env": brave_env}
		
]
drafter_mcp_server_params = [
    {
        "command": "uv",
        "args": ["run", "draft_server.py"],
        "working_directory": server_directory
    },
    {
        "command": "uv",
        "args": ["run", "push_server.py"],
        "working_directory": server_directory
    }
]
