"""
MCP Server for searching the MLB Draft Oracle knowledge base (S3 Vectors).
"""
import os
import sys
import json
import boto3
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from mcp.server.fastmcp import FastMCP
from typing import List, Dict, Any

# Load environment variables
load_dotenv(override=True, dotenv_path=find_dotenv())

# Get configuration from environment
VECTOR_BUCKET = os.getenv('VECTOR_BUCKET')
SAGEMAKER_ENDPOINT = os.getenv('SAGEMAKER_ENDPOINT', 'mlbdraftoracle-embedding-endpoint')
INDEX_NAME = 'draft-research'

# Initialize AWS clients
try:
    s3_vectors = boto3.client('s3vectors')
    sagemaker_runtime = boto3.client('sagemaker-runtime')
    CLIENTS_AVAILABLE = True
    print("AWS clients initialized successfully")
except Exception as e:
    print(f"Warning: Could not initialize AWS clients: {e}")
    CLIENTS_AVAILABLE = False

# Initialize FastMCP server
mcp = FastMCP(
    name="knowledgebase_server",
    instructions="""You provide access to the MLB Draft Oracle knowledge base.
    This knowledge base contains research and analysis on MLB players, including:
    - Recent performance data and statistics
    - Injury reports and player health status
    - Fantasy baseball rankings and projections
    - Team news and roster changes
    - Historical performance trends
    
    Use this tool to search for relevant information when making draft decisions."""
)


def get_embedding(text: str) -> List[float]:
    """
    Get embedding vector from SageMaker endpoint.
    
    Args:
        text: The text to embed
        
    Returns:
        List of floats representing the embedding vector
    """
    if not CLIENTS_AVAILABLE:
        raise Exception("AWS clients not available")
    
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT,
        ContentType='application/json',
        Body=json.dumps({'inputs': text})
    )
    
    result = json.loads(response['Body'].read().decode())
    
    # HuggingFace returns nested array [[[embedding]]], extract the actual embedding
    if isinstance(result, list) and len(result) > 0:
        if isinstance(result[0], list) and len(result[0]) > 0:
            if isinstance(result[0][0], list):
                return result[0][0]  # Extract from [[[embedding]]]
            return result[0]  # Extract from [[embedding]]
    return result  # Return as-is if not nested


@mcp.tool()
async def search_knowledgebase(query: str, top_k: int = 5) -> str:
    """
    Search the MLB Draft Oracle knowledge base for relevant information.
    
    Args:
        query: The search query (e.g., "Bryce Harper recent performance", 
               "top catchers 2025", "injury reports pitchers")
        top_k: Number of results to return (default: 5, max: 10)
    
    Returns:
        JSON string containing search results with relevance scores and content
    """
    if not CLIENTS_AVAILABLE:
        return json.dumps({
            "error": "Knowledge base not available - AWS clients not initialized",
            "results": []
        })
    
    if not VECTOR_BUCKET:
        return json.dumps({
            "error": "Knowledge base not configured - VECTOR_BUCKET not set",
            "results": []
        })
    
    # Validate top_k
    top_k = min(max(1, top_k), 10)
    
    try:
        # Get embedding for query
        print(f"Searching knowledge base for: {query}")
        query_embedding = get_embedding(query)
        
        # Search S3 Vectors
        response = s3_vectors.query_vectors(
            vectorBucketName=VECTOR_BUCKET,
            indexName=INDEX_NAME,
            queryVector={"float32": query_embedding},
            topK=top_k,
            returnDistance=True,
            returnMetadata=True
        )
        
        # Format results
        results = []
        for vector in response.get('vectors', []):
            metadata = vector.get('metadata', {})
            distance = vector.get('distance', 1.0)
            similarity_score = 1 - distance  # Convert distance to similarity
            
            results.append({
                'relevance_score': round(similarity_score, 3),
                'content': metadata.get('text', ''),
                'topic': metadata.get('topic', 'Unknown'),
                'timestamp': metadata.get('timestamp', 'Unknown'),
                'id': vector.get('key', '')
            })
        
        # Sort by relevance score descending
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return json.dumps({
            "query": query,
            "results_count": len(results),
            "results": results
        }, indent=2)
        
    except Exception as e:
        error_msg = f"Error searching knowledge base: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        
        return json.dumps({
            "error": error_msg,
            "query": query,
            "results": []
        })


if __name__ == "__main__":
    print("Starting MCP knowledge base server...")
    print(f"Vector Bucket: {VECTOR_BUCKET}")
    print(f"Index Name: {INDEX_NAME}")
    print(f"Clients Available: {CLIENTS_AVAILABLE}")
    mcp.run(transport='stdio')