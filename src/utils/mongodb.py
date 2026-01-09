"""MongoDB utilities for article storage."""

import os
import logging
from typing import Optional
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError

logger = logging.getLogger(__name__)

# MongoDB connection string from environment
# Railway MongoDB add-on provides MONGO_URL automatically
MONGO_URL = os.getenv('MONGO_URL')
DATABASE_NAME = os.getenv('MONGODB_DATABASE', 'opad')
COLLECTION_NAME = 'articles'

_client_cache = None
_connection_attempted = False
_connection_failed = False


def get_mongodb_client() -> Optional[MongoClient]:
    """Get MongoDB client with connection caching and reconnection logic.
    
    Connection strategy:
    1. Return cached client if healthy (ping succeeds)
    2. If cached client fails, attempt reconnection
    3. If initial connection failed (config issue), don't retry
    
    Returns:
        MongoDB client or None if connection fails
    """
    global _client_cache, _connection_attempted, _connection_failed
    
    # Fast path: return cached client if healthy
    if _client_cache:
        try:
            _client_cache.admin.command('ping')
            return _client_cache
        except:
            _client_cache = None
            logger.debug("[MONGODB] Cached client failed ping, attempting reconnection...")
    
    # Don't retry if initial connection failed (configuration issue)
    if _connection_failed:
        return None
    
    # Validate connection string is configured
    if not MONGO_URL:
        logger.error("[MONGODB] MONGO_URL not configured.")
        logger.error("[MONGODB] Railway MongoDB add-on provides MONGO_URL automatically.")
        _connection_failed = True
        return None
    
    # Attempt connection
    try:
        client = MongoClient(
            MONGO_URL,
            serverSelectionTimeoutMS=5000  # 5s timeout
        )
        client.admin.command('ping')  # Verify connection works
        
        # Track first successful connection
        is_first_connection = not _connection_attempted
        _connection_attempted = True
        
        # Cache for future calls
        _client_cache = client
        
        # Log only on first connection
        if is_first_connection:
            logger.info(f"[MONGODB] Connected successfully to {DATABASE_NAME}")
        
        return client
    except (ConnectionFailure, PyMongoError) as e:
        # Log only on initial failure
        if not _connection_attempted:
            error_msg = str(e)[:200]
            logger.error(f"[MONGODB] Initial connection failed: {error_msg}")
            logger.error(f"[MONGODB] Railway provides MONGO_URL automatically from MongoDB add-on")
            _connection_failed = True
        return None


def save_article(article_id: str, content: str, language: str, level: str, 
                 length: str, topic: str) -> bool:
    """Save article to MongoDB.
    
    This function saves both metadata and content to MongoDB.
    If article already exists, it updates the content and metadata.
    
    Args:
        article_id: Unique article identifier
        content: Markdown content
        language: Target language
        level: Language level (A1-C2)
        length: Target word count
        topic: Article topic
        
    Returns:
        True if successful, False otherwise
    """
    client = get_mongodb_client()
    if not client:
        return False
    
    try:
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        article_doc = {
            '_id': article_id,
            'content': content,
            'language': language,
            'level': level,
            'length': length,
            'topic': topic,
            'status': 'completed',
            'updated_at': datetime.utcnow()
        }
        
        # Use upsert to handle both insert and update
        collection.update_one(
            {'_id': article_id},
            {
                '$set': article_doc,
                '$setOnInsert': {'created_at': datetime.utcnow()}
            },
            upsert=True
        )
        
        logger.info(f"Article {article_id} saved to MongoDB")
        return True
    except PyMongoError as e:
        logger.error(f"Failed to save article {article_id}: {e}")
        return False


def get_article(article_id: str) -> Optional[dict]:
    """Get article from MongoDB.
    
    Args:
        article_id: Article identifier
        
    Returns:
        Article document (with content) or None if not found
    """
    client = get_mongodb_client()
    if not client:
        return None
    
    try:
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        article = collection.find_one({'_id': article_id})
        return article
    except PyMongoError as e:
        logger.error(f"Failed to get article {article_id}: {e}")
        return None


def save_article_metadata(article_id: str, language: str, level: str, 
                          length: str, topic: str, status: str = 'pending') -> bool:
    """Save article metadata to MongoDB (without content).
    
    Used when creating article before generation starts.
    
    Args:
        article_id: Unique article identifier
        language: Target language
        level: Language level (A1-C2)
        length: Target word count
        topic: Article topic
        status: Article status (default: 'pending')
        
    Returns:
        True if successful, False otherwise
    """
    client = get_mongodb_client()
    if not client:
        return False
    
    try:
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        article_doc = {
            '_id': article_id,
            'language': language,
            'level': level,
            'length': length,
            'topic': topic,
            'status': status,
            'updated_at': datetime.utcnow()
        }
        
        # Use upsert to handle both insert and update
        collection.update_one(
            {'_id': article_id},
            {
                '$set': article_doc,
                '$setOnInsert': {'created_at': datetime.utcnow()}
            },
            upsert=True
        )
        
        logger.info(f"Article metadata {article_id} saved to MongoDB")
        return True
    except PyMongoError as e:
        logger.error(f"Failed to save article metadata {article_id}: {e}")
        return False
