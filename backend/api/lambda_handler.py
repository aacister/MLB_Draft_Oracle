# ============================================================================
# backend/api/lambda_handler.py - REFACTORED VERSION
# ============================================================================
from mangum import Mangum
from backend.api.main import app
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Lambda handler with PostgreSQL RDS support using DB_URL.
    """
    try:
        logger.info(f"Received event: {event.get('httpMethod')} {event.get('path')}")
        logger.info("Using PostgreSQL RDS via DB_URL environment variable")
        
        # Handle OPTIONS requests directly for CORS preflight
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'DELETE,GET,HEAD,OPTIONS,PATCH,POST,PUT',
                    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                    'Access-Control-Max-Age': '86400'
                },
                'body': ''
            }
        
        # Verify DB_URL is available
        db_url = os.getenv('DB_URL')
        if not db_url:
            logger.error("DB_URL not set - PostgreSQL RDS connection required")
            return {
                'statusCode': 500,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': '{"error": "Database configuration error", "message": "DB_URL not configured"}'
            }
        
        logger.info("PostgreSQL RDS connection configured via DB_URL")
        
        # Use Mangum to handle the request
        asgi_handler = Mangum(app, lifespan="off")
        response = asgi_handler(event, context)
        
        # Ensure CORS headers are in response
        if 'headers' not in response:
            response['headers'] = {}
        
        response['headers']['Access-Control-Allow-Origin'] = '*'
        response['headers']['Access-Control-Allow-Methods'] = 'DELETE,GET,HEAD,OPTIONS,PATCH,POST,PUT'
        response['headers']['Access-Control-Allow-Headers'] = 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
        
        return response
        
    except Exception as e:
        logger.error(f"Error in Lambda handler: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': f'{{"error": "Internal Server Error", "message": "{str(e)}"}}'
        }