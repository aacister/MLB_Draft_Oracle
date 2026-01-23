"""
Lambda MCP client adapter (manual implementation - no external package needed).
Replaces stdio-based MCP servers with Lambda function invocations.
"""
import json
import logging
import boto3
import os
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Initialize Lambda client
lambda_client = boto3.client('lambda', region_name=os.getenv('AWS_REGION', 'us-east-2'))


class LambdaMCPClient:
    """
    Client that invokes Lambda functions instead of stdio processes.
    Compatible with existing MCP client interface.
    """
    
    def __init__(self, function_name: str):
        self.function_name = function_name
        logger.info(f"Initialized Lambda MCP client for: {function_name}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool via Lambda invocation.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        payload = {
            'jsonrpc': '2.0',
            'method': 'tools/call',
            'params': {
                'name': tool_name,
                'arguments': arguments
            },
            'id': 1
        }
        
        logger.info(f"[LambdaMCPClient] Invoking {self.function_name}.{tool_name}")
        
        try:
            response = lambda_client.invoke(
                FunctionName=self.function_name,
                InvocationType='RequestResponse',  # Synchronous
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read().decode())
            
            if 'error' in result:
                error_msg = result['error'].get('message', 'Unknown error')
                logger.error(f"[LambdaMCPClient] ✗ {tool_name} failed: {error_msg}")
                raise Exception(f"Tool call failed: {error_msg}")
            
            logger.info(f"[LambdaMCPClient] ✓ {tool_name} succeeded")
            return result.get('result')
        
        except Exception as e:
            logger.error(f"[LambdaMCPClient] Error invoking {tool_name}: {e}", exc_info=True)
            raise
    
    async def list_tools(self) -> List[Dict]:
        """
        List available tools from the Lambda function.
        
        Returns:
            List of tool definitions
        """
        payload = {
            'jsonrpc': '2.0',
            'method': 'tools/list',
            'id': 1
        }
        
        logger.info(f"[LambdaMCPClient] Listing tools from {self.function_name}")
        
        try:
            response = lambda_client.invoke(
                FunctionName=self.function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read().decode())
            
            if 'error' in result:
                error_msg = result['error'].get('message', 'Unknown error')
                logger.error(f"[LambdaMCPClient] ✗ list_tools failed: {error_msg}")
                return []
            
            tools = result.get('result', {}).get('tools', [])
            logger.info(f"[LambdaMCPClient] ✓ Found {len(tools)} tools")
            return tools
        
        except Exception as e:
            logger.error(f"[LambdaMCPClient] Error listing tools: {e}", exc_info=True)
            return []
    
    async def read_resource(self, uri: str) -> str:
        """
        Read a resource via Lambda invocation.
        
        Args:
            uri: Resource URI
            
        Returns:
            Resource content
        """
        payload = {
            'jsonrpc': '2.0',
            'method': 'resources/read',
            'params': {
                'uri': uri
            },
            'id': 1
        }
        
        logger.info(f"[LambdaMCPClient] Reading resource: {uri}")
        
        try:
            response = lambda_client.invoke(
                FunctionName=self.function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read().decode())
            
            if 'error' in result:
                error_msg = result['error'].get('message', 'Unknown error')
                logger.error(f"[LambdaMCPClient] ✗ read_resource failed: {error_msg}")
                raise Exception(f"Resource read failed: {error_msg}")
            
            contents = result.get('result', {}).get('contents', [])
            if contents and len(contents) > 0:
                logger.info(f"[LambdaMCPClient] ✓ Resource read successfully")
                return contents[0].get('text', '')
            return ''
        
        except Exception as e:
            logger.error(f"[LambdaMCPClient] Error reading resource: {e}", exc_info=True)
            raise


# Factory functions for creating clients
def get_draft_mcp_client() -> LambdaMCPClient:
    """Get Lambda MCP client for draft server"""
    function_name = os.getenv('DRAFT_MCP_LAMBDA', 'mlb-draft-oracle-mcp-draft')
    return LambdaMCPClient(function_name)


def get_knowledgebase_mcp_client() -> LambdaMCPClient:
    """Get Lambda MCP client for knowledgebase server"""
    function_name = os.getenv('KNOWLEDGEBASE_MCP_LAMBDA', 'mlb-draft-oracle-mcp-knowledgebase')
    return LambdaMCPClient(function_name)


def get_brave_search_mcp_client() -> LambdaMCPClient:
    """Get Lambda MCP client for brave search server"""
    function_name = os.getenv('BRAVE_SEARCH_MCP_LAMBDA', 'mlb-draft-oracle-mcp-brave-search')
    return LambdaMCPClient(function_name)