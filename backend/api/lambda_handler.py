from mangum import Mangum
from backend.api.main import app
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Lambda handler with PostgreSQL RDS support ONLY.
    SQLite support has been removed.
    """
    try:
        logger.info(f"Received event: {event.get('httpMethod')} {event.get('path')}")
        logger.info("Using PostgreSQL RDS exclusively")
        
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
        
        # Verify PostgreSQL RDS credentials are available
        db_secret_arn = os.getenv('DB_SECRET_ARN')
        if not db_secret_arn:
            logger.error("DB_SECRET_ARN not set - PostgreSQL RDS is required")
            return {
                'statusCode': 500,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': '{"error": "Database configuration error", "message": "DB_SECRET_ARN not configured"}'
            }
        
        logger.info(f"Using PostgreSQL RDS with secret: {db_secret_arn}")
        
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