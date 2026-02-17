"""
backend/data/rag/vector_indexer.py

Vector Indexer Core Logic
Processes draft history files and creates vector embeddings for RAG search
"""

import json
import boto3
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from openai import OpenAI

logger = logging.getLogger(__name__)

# Initialize clients
s3 = boto3.client('s3')
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# Configuration
VECTOR_BUCKET = os.environ.get('S3_MEMORY_BUCKET', 'mlbdraftoracle-memory-425865275846')
SOURCE_PREFIX = 'source_data/historical_drafts/'
VECTOR_INDEX_PREFIX = 'vectors/draft-insights/'
EMBEDDING_MODEL = 'text-embedding-3-small'  # 1536 dimensions, $0.02/1M tokens


def get_embedding(text: str) -> List[float]:
    """
    Generate embedding vector using OpenAI
    
    Args:
        text: Text to embed
        
    Returns:
        List of 1536 floats (embedding vector)
    """
    try:
        response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise


def extract_insights_from_draft(draft_data: Dict) -> List[Dict]:
    """
    Extract searchable insights from draft data.
    Each insight becomes a separate vector document.
    
    Args:
        draft_data: Parsed draft JSON
        
    Returns:
        List of insight documents to be vectorized
    """
    
    insights = []
    draft_id = draft_data.get('draft_id', 'unknown')
    
    # Extract team-level insights
    for team in draft_data.get('teams', []):
        team_name = team.get('name')
        strategy = team.get('strategy')
        filled_positions = team.get('filled_positions', [])
        needed_positions = team.get('needed_positions', [])
        
        # Insight: Team roster status
        roster_text = f"Team {team_name} uses {strategy} strategy. "
        
        if filled_positions:
            roster_text += f"Filled positions: "
            roster_text += ", ".join([f"{p['position']} ({p['player']})" for p in filled_positions])
            roster_text += ". "
        
        if needed_positions:
            roster_text += f"Still needs: {', '.join(needed_positions)}."
        else:
            roster_text += "Roster is complete."
        
        insights.append({
            'type': 'team_roster',
            'draft_id': draft_id,
            'team_name': team_name,
            'strategy': strategy,
            'content': roster_text,
            'metadata': {
                'filled_count': len(filled_positions),
                'needed_count': len(needed_positions),
                'roster_complete': len(needed_positions) == 0
            }
        })
    
    # Extract pick-level insights
    for pick in draft_data.get('picks', []):
        if not pick.get('player_name'):
            continue  # Skip empty picks
        
        team_name = pick.get('team_name')
        strategy = pick.get('strategy')
        player_name = pick.get('player_name')
        position = pick.get('position')
        round_num = pick.get('round')
        rationale = pick.get('rationale', '')
        
        # Insight: Individual pick with context
        pick_text = (
            f"In round {round_num}, team {team_name} (strategy: {strategy}) "
            f"drafted {player_name} at position {position}. "
        )
        
        if rationale:
            pick_text += f"Rationale: {rationale}"
        
        insights.append({
            'type': 'draft_pick',
            'draft_id': draft_id,
            'team_name': team_name,
            'strategy': strategy,
            'player_name': player_name,
            'position': position,
            'round': round_num,
            'content': pick_text,
            'metadata': {
                'pick_number': pick.get('pick'),
                'timestamp': pick.get('timestamp')
            }
        })
    
    # Extract strategy patterns (if multiple picks exist)
    picks = draft_data.get('picks', [])
    if len(picks) >= 2:
        # Group picks by strategy
        strategy_picks = {}
        for pick in picks:
            if not pick.get('player_name'):
                continue
            strategy = pick.get('strategy', 'Unknown')
            if strategy not in strategy_picks:
                strategy_picks[strategy] = []
            strategy_picks[strategy].append(pick)
        
        # Create strategy pattern insights
        for strategy, strategy_pick_list in strategy_picks.items():
            positions_drafted = [p.get('position') for p in strategy_pick_list if p.get('position')]
            
            if positions_drafted:
                pattern_text = (
                    f"{strategy} strategy teams in this draft prioritized: "
                    f"{', '.join(positions_drafted)}. "
                    f"Total picks: {len(strategy_pick_list)}."
                )
                
                insights.append({
                    'type': 'strategy_pattern',
                    'draft_id': draft_id,
                    'strategy': strategy,
                    'content': pattern_text,
                    'metadata': {
                        'positions': positions_drafted,
                        'pick_count': len(strategy_pick_list)
                    }
                })
    
    logger.info(f"Extracted {len(insights)} insights from draft {draft_id}")
    return insights


def index_draft_file(s3_key: str) -> Dict:
    """
    Index a single draft file from S3.
    
    Process:
    1. Load draft JSON from S3
    2. Extract insights
    3. Generate embeddings
    4. Store vectors in S3
    
    Args:
        s3_key: S3 key of draft file (e.g., 'source_data/historical_drafts/draft_X_current.json')
        
    Returns:
        Dict with indexing results
    """
    
    logger.info(f"Indexing draft file: {s3_key}")
    
    try:
        # 1. Load draft data from S3
        obj = s3.get_object(Bucket=VECTOR_BUCKET, Key=s3_key)
        draft_data = json.loads(obj['Body'].read())
        
        draft_id = draft_data.get('draft_id', 'unknown')
        logger.info(f"Processing draft: {draft_id}")
        
        # 2. Extract insights
        insights = extract_insights_from_draft(draft_data)
        
        if not insights:
            logger.warning(f"No insights extracted from {s3_key}")
            return {
                'success': True,
                'draft_id': draft_id,
                'insights_indexed': 0,
                'message': 'No insights to index'
            }
        
        # 3. Generate embeddings and store vectors
        indexed_count = 0
        
        for i, insight in enumerate(insights):
            try:
                # Generate embedding
                content = insight['content']
                embedding = get_embedding(content)
                
                # Create vector document
                vector_doc = {
                    'id': f"{draft_id}_{insight['type']}_{i}",
                    'draft_id': draft_id,
                    'type': insight['type'],
                    'content': content,
                    'embedding': embedding,
                    'metadata': {
                        **insight.get('metadata', {}),
                        'team_name': insight.get('team_name'),
                        'strategy': insight.get('strategy'),
                        'position': insight.get('position'),
                        'player_name': insight.get('player_name'),
                        'round': insight.get('round'),
                        'indexed_at': datetime.utcnow().isoformat()
                    }
                }
                
                # Store in S3
                vector_key = f"{VECTOR_INDEX_PREFIX}{vector_doc['id']}.json"
                s3.put_object(
                    Bucket=VECTOR_BUCKET,
                    Key=vector_key,
                    Body=json.dumps(vector_doc, default=str),
                    ContentType='application/json'
                )
                
                indexed_count += 1
                
            except Exception as e:
                logger.error(f"Error indexing insight {i}: {e}")
                continue
        
        logger.info(f"✅ Indexed {indexed_count}/{len(insights)} insights from {draft_id}")
        
        return {
            'success': True,
            'draft_id': draft_id,
            'insights_extracted': len(insights),
            'insights_indexed': indexed_count,
            'vector_location': f"s3://{VECTOR_BUCKET}/{VECTOR_INDEX_PREFIX}"
        }
        
    except Exception as e:
        logger.error(f"Error indexing draft file {s3_key}: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            's3_key': s3_key
        }


def search_vectors(query: str, top_k: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
    """
    Search vector index for similar content.
    
    Args:
        query: Search query text
        top_k: Number of results to return
        filters: Optional metadata filters (e.g., {'strategy': 'Power Hitting'})
        
    Returns:
        List of matching documents with similarity scores
    """
    
    logger.info(f"Searching vectors for: {query}")
    
    try:
        # 1. Generate query embedding
        query_embedding = get_embedding(query)
        
        # 2. List all vector documents
        response = s3.list_objects_v2(
            Bucket=VECTOR_BUCKET,
            Prefix=VECTOR_INDEX_PREFIX
        )
        
        if 'Contents' not in response:
            logger.warning("No vectors found in index")
            return []
        
        # 3. Load and score each vector
        results = []
        
        for obj in response['Contents']:
            try:
                # Load vector document
                vector_obj = s3.get_object(Bucket=VECTOR_BUCKET, Key=obj['Key'])
                vector_doc = json.loads(vector_obj['Body'].read())
                
                # Apply filters if provided
                if filters:
                    metadata = vector_doc.get('metadata', {})
                    skip = False
                    for key, value in filters.items():
                        if metadata.get(key) != value:
                            skip = True
                            break
                    if skip:
                        continue
                
                # Calculate cosine similarity
                doc_embedding = vector_doc['embedding']
                similarity = cosine_similarity(query_embedding, doc_embedding)
                
                results.append({
                    'id': vector_doc.get('id'),
                    'draft_id': vector_doc.get('draft_id'),
                    'type': vector_doc.get('type'),
                    'content': vector_doc.get('content'),
                    'metadata': vector_doc.get('metadata', {}),
                    'similarity_score': similarity
                })
                
            except Exception as e:
                logger.warning(f"Error processing vector {obj['Key']}: {e}")
                continue
        
        # 4. Sort by similarity and return top_k
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        results = results[:top_k]
        
        logger.info(f"Found {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Error searching vectors: {e}", exc_info=True)
        return []


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Similarity score between 0 and 1
    """
    import math
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)