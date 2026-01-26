import sys
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(override=True, dotenv_path=find_dotenv())

# Detect Lambda environment
IS_LAMBDA = os.path.exists("/var/task")
WORKING_DIR = "/var/task" if IS_LAMBDA else os.getcwd()
PYTHON_CMD = "/var/lang/bin/python3" if IS_LAMBDA else "python"

brave_api_key = os.getenv("BRAVE_API_KEY")
brave_env = {
    "BRAVE_API_KEY": brave_api_key,
    "HOME": "/tmp",
    "TMPDIR": "/tmp",
    "XDG_CONFIG_HOME": "/tmp",
    "XDG_CACHE_HOME": "/tmp",
    "XDG_DATA_HOME": "/tmp",      
    "XDG_RUNTIME_DIR": "/tmp",
    "XDG_STATE_HOME": "/tmp",
    "XDG_CONFIG_DIRS": "/tmp",
    "XDG_DATA_DIRS": "/tmp",
    "PATH": os.environ.get("PATH", ""),
    "NODE_PATH": "/usr/lib/node_modules",
}

print(f"Working directory: {WORKING_DIR}")
print(f"Is Lambda: {IS_LAMBDA}")
print(f"Python command: {PYTHON_CMD}")

# Environment for Python MCP servers - UPDATED TO USE DB_URL
python_env = {
    "PYTHONPATH": WORKING_DIR,
    "PATH": os.environ.get("PATH", ""),
    # Database connection via DB_URL
    "DB_URL": os.getenv("DB_URL", ""),
    # AWS Region
    "AWS_REGION": os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-2")),
    "AWS_REGION_NAME": os.getenv("AWS_REGION_NAME", os.getenv("AWS_REGION", "us-east-2")),
    # Pass AWS credentials if available (Lambda execution role provides these)
    "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID", ""),
    "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY", ""),
    "AWS_SESSION_TOKEN": os.getenv("AWS_SESSION_TOKEN", ""),
    # Pass other API keys that might be needed
    "BRAVE_API_KEY": os.getenv("BRAVE_API_KEY", ""),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
    # Deployment environment
    "DEPLOYMENT_ENVIRONMENT": os.getenv("DEPLOYMENT_ENVIRONMENT", "LAMBDA" if IS_LAMBDA else "DEV"),
}

# Clean up empty values to avoid issues
python_env = {k: v for k, v in python_env.items() if v}

drafter_mcp_server_params = [
    {
        "command": PYTHON_CMD,
        "args": [f"{WORKING_DIR}/mcp_servers/draft_server.py"],
        "working_directory": WORKING_DIR,
        "env": python_env
    }
]

# In Lambda, use the pre-installed global package
if IS_LAMBDA:
    researcher_mcp_server_params = [
        {
            "command": PYTHON_CMD,
            "args": [f"{WORKING_DIR}/mcp_servers/brave_search_wrapper.py"],
            "working_directory": WORKING_DIR,
            "env": brave_env
        }
    ]
else:
    # Local dev: use npx
    researcher_mcp_server_params = [
        {
            "command": "npx",
            "args": ["-y", "@brave/brave-search-mcp-server"],
            "env": brave_env,
            "working_directory": WORKING_DIR
        }
    ]

# Knowledge base server configuration
knowledgebase_mcp_server_params = [
    {
        "command": PYTHON_CMD,
        "args": [f"{WORKING_DIR}/mcp_servers/knowledgebase_server.py"],
        "working_directory": WORKING_DIR,
        "env": python_env
    }
]