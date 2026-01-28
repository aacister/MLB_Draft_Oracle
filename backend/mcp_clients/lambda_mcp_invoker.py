"""
MCP Client that invokes separate Lambda functions for MCP operations
"""

import json
import logging
import boto3
import os

logger = logging.getLogger(__name__)

lambda_client = boto3.client('lambda', region_name=os.getenv('AWS_REGION', 'us-east-2'))


class LambdaMCPInvoker:
    """Invokes MCP Lambda functions for tool calls"""
    
    def __init__(self, lambda_function_name: str):
        self.lambda_function_name = lambda_function_name
    
    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call a tool by invoking the MCP Lambda function"""
        logger.info(f"[LambdaMCPInvoker] Invoking {self.lambda_function_name} for tool {tool_name}")
        
        payload = {
            "action": "call_tool",
            "tool_name": tool_name,
            "arguments": arguments
        }
        
        try:
            response = lambda_client.invoke(
                FunctionName=self.lambda_function_name,
                InvocationType='RequestResponse',  # Synchronous
                Payload=json.dumps(payload)
            )
            
            response_payload = json.loads(response['Payload'].read())
            
            if response_payload.get('statusCode') == 200:
                body = json.loads(response_payload['body'])
                logger.info(f"[LambdaMCPInvoker] ✓ Tool call successful")
                return body
            else:
                error = response_payload.get('body', 'Unknown error')
                logger.error(f"[LambdaMCPInvoker] ✗ Tool call failed: {error}")
                return {"status": "error", "error": error}
        
        except Exception as e:
            logger.error(f"[LambdaMCPInvoker] ✗ Error invoking Lambda: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    async def list_tools(self) -> list:
        """List available tools from the MCP Lambda"""
        logger.info(f"[LambdaMCPInvoker] Listing tools from {self.lambda_function_name}")
        
        payload = {
            "action": "list_tools"
        }
        
        try:
            response = lambda_client.invoke(
                FunctionName=self.lambda_function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            response_payload = json.loads(response['Payload'].read())
            
            if response_payload.get('statusCode') == 200:
                body = json.loads(response_payload['body'])
                tools = body.get('tools', [])
                logger.info(f"[LambdaMCPInvoker] ✓ Got {len(tools)} tools")
                return tools
            else:
                logger.error(f"[LambdaMCPInvoker] ✗ Failed to list tools")
                return []
        
        except Exception as e:
            logger.error(f"[LambdaMCPInvoker] ✗ Error listing tools: {e}", exc_info=True)
            return []


# Singleton instances
_draft_invoker = None
_search_invoker = None


def get_draft_mcp_invoker() -> LambdaMCPInvoker:
    """Get singleton instance for draft MCP Lambda"""
    global _draft_invoker
    if _draft_invoker is None:
        _draft_invoker = LambdaMCPInvoker("mlb-draft-oracle-mcp-draft")
    return _draft_invoker


def get_search_mcp_invoker() -> LambdaMCPInvoker:
    """Get singleton instance for search MCP Lambda"""
    global _search_invoker
    if _search_invoker is None:
        _search_invoker = LambdaMCPInvoker("mlb-draft-oracle-mcp-brave-search")
    return _search_invoker