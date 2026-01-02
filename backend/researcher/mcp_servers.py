
import os
from typing import Dict, Any
from dotenv import load_dotenv, find_dotenv

load_dotenv(override=True, dotenv_path=find_dotenv())
brave_api_key = os.getenv("BRAVE_API_KEY")

# Validate that BRAVE_API_KEY is set
if not brave_api_key:
    raise ValueError(
        "BRAVE_API_KEY environment variable is not set. "
        "Please set it in your .env file or as an environment variable. "
        "Get your API key from: https://api.search.brave.com/"
    )

# Merge with existing environment to preserve PATH and other variables
brave_env = os.environ.copy()
brave_env["BRAVE_API_KEY"] = brave_api_key

researcher_mcp_server_params = [
    {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-brave-search"], "env": brave_env}
		
]