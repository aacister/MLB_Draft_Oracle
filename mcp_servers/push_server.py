#!/usr/bin/env python3
from dotenv import load_dotenv
from pathlib import Path
import requests
from pydantic import BaseModel, Field
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv(override=True)

pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("push_server")

class PushModelArgs(BaseModel):
    message: str = Field(description="A brief message to push")

@mcp.tool()
def push(args: PushModelArgs):
    """ Send a push notification with this brief message """
    print(f"Push: {args.message}")
    payload = {"user": pushover_user, "token": pushover_token, "message": args.message}
    requests.post(pushover_url, data=payload)

if __name__ == "__main__":
    mcp.run(transport='stdio')