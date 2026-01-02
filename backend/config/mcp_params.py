import sys
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(override=True, dotenv_path=find_dotenv())

brave_api_key = os.getenv("BRAVE_API_KEY")
brave_env = {
    "BRAVE_API_KEY": os.getenv("BRAVE_API_KEY"),
    "HOME": "/tmp",
    "TMPDIR": "/tmp",
    "XDG_CONFIG_HOME": "/tmp",
    "XDG_CACHE_HOME": "/tmp",
    "XDG_DATA_HOME": "/tmp",      
    "XDG_RUNTIME_DIR": "/tmp",
    "XDG_STATE_HOME": "/tmp",
    "XDG_CONFIG_DIRS": "/tmp",
    "XDG_DATA_DIRS": "/tmp",
    "XDG_CACHE_DIRS": "/tmp",
    "XDG_RUNTIME_DIR": "/tmp",
    "XDG_STATE_DIR": "/tmp",
    }

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
    {
        "command": "npx", 
        "args": ["-y", "@modelcontextprotocol/server-brave-search"], 
        "env": brave_env
    }
]


# Knowledge base server configuration
knowledgebase_mcp_server_params = [
    {
        "command": "python",
        "args": ["mcp_servers/knowledgebase_server.py"],
        "working_directory": "/app"
    }
]