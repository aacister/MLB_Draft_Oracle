"""
backend/lambda/rag/indexer_handler.py

Lambda Handler for Vector Indexer
Triggered by S3 events when draft files are created/updated
"""

import json
import logging
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, '/var/task')
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def handler(event, context):
    """
    Lambda handler triggered by S3 events.
    
    Event format (S3 notification):
    {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "mlbdraftoracle-memory-425865275846"},
                    "object": {"key": "source_data/historical_drafts/draft_X_current.json"}
                }
            }
        ]
    }
    
    Or manual invocation:
    {
        "action": "index",
        "s3_key": "source_data/historical_drafts/draft_X_current.json"
    }
    
    Or manual search:
    {
        "action": "search",
        "query": "What positions did Power Hitting teams draft?",
        "top_k": 5
    }
    """
    
    logger.info("=" * 80)
    logger.info("MLB DRAFT ORACLE - VECTOR INDEXER")
    logger.info("=" * 80)
    logger.info(f"Event: {json.dumps(event, default=str)[:500]}")
    
    try:
        from backend.data.rag.vector_indexer import index_draft_file, search_vectors
        
        # Case 1: S3 Event Trigger
        if 'Records' in event:
            logger.info("Processing S3 event trigger")
            
            results = []
            
            for record in event['Records']:
                s3_info = record.get('s3', {})
                bucket = s3_info.get('bucket', {}).get('name')
                s3_key = s3_info.get('object', {}).get('key')
                
                logger.info(f"Processing file: s3://{bucket}/{s3_key}")
                
                # Only process draft history files
                if not s3_key.startswith('source_data/historical_drafts/'):
                    logger.info(f"Skipping non-draft file: {s3_key}")
                    continue
                
                # Index the file
                result = index_draft_file(s3_key)
                results.append(result)
            
            # Summary
            successful = len([r for r in results if r.get('success')])
            total_insights = sum([r.get('insights_indexed', 0) for r in results])
            
            logger.info("=" * 80)
            logger.info(f"INDEXING COMPLETE: {successful}/{len(results)} files")
            logger.info(f"Total insights indexed: {total_insights}")
            logger.info("=" * 80)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'success',
                    'files_processed': len(results),
                    'files_successful': successful,
                    'total_insights_indexed': total_insights,
                    'results': results
                })
            }
        
        # Case 2: Manual Index Request
        elif event.get('action') == 'index':
            logger.info("Processing manual index request")
            
            s3_key = event.get('s3_key')
            
            if not s3_key:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'status': 'error',
                        'error': 's3_key parameter required'
                    })
                }
            
            result = index_draft_file(s3_key)
            
            logger.info("=" * 80)
            logger.info("MANUAL INDEXING COMPLETE")
            logger.info("=" * 80)
            
            return {
                'statusCode': 200 if result.get('success') else 500,
                'body': json.dumps(result)
            }
        
        # Case 3: Manual Search Request
        elif event.get('action') == 'search':
            logger.info("Processing manual search request")
            
            query = event.get('query')
            top_k = event.get('top_k', 5)
            filters = event.get('filters')
            
            if not query:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'status': 'error',
                        'error': 'query parameter required'
                    })
                }
            
            results = search_vectors(query, top_k, filters)
            
            logger.info("=" * 80)
            logger.info(f"SEARCH COMPLETE: Found {len(results)} results")
            logger.info("=" * 80)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'success',
                    'query': query,
                    'results_count': len(results),
                    'results': results
                })
            }
        
        # Case 4: Index All Existing Files
        elif event.get('action') == 'index_all':
            logger.info("Processing index_all request")
            
            import boto3
            s3_client = boto3.client('s3')
            
            # List all draft files
            bucket = os.environ.get('S3_MEMORY_BUCKET', 'mlbdraftoracle-memory-425865275846')
            prefix = 'source_data/historical_drafts/'
            
            response = s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'status': 'success',
                        'message': 'No draft files found',
                        'files_indexed': 0
                    })
                }
            
            results = []
            
            for obj in response['Contents']:
                s3_key = obj['Key']
                
                # Skip directories
                if s3_key.endswith('/'):
                    continue
                
                logger.info(f"Indexing: {s3_key}")
                result = index_draft_file(s3_key)
                results.append(result)
            
            successful = len([r for r in results if r.get('success')])
            total_insights = sum([r.get('insights_indexed', 0) for r in results])
            
            logger.info("=" * 80)
            logger.info(f"BULK INDEXING COMPLETE: {successful}/{len(results)} files")
            logger.info(f"Total insights indexed: {total_insights}")
            logger.info("=" * 80)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'success',
                    'files_processed': len(results),
                    'files_successful': successful,
                    'total_insights_indexed': total_insights
                })
            }
        
        # Unknown action
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'status': 'error',
                    'error': 'Unknown action or event type',
                    'supported_actions': ['index', 'search', 'index_all']
                })
            }
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error("ERROR IN VECTOR INDEXER")
        logger.error("=" * 80)
        logger.error(f"Error: {e}", exc_info=True)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'error': str(e)
            })
        }