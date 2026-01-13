"""MongoDB utilities for article storage."""

import os
import logging
from typing import Optional
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError

logger = logging.getLogger(__name__)

# Suppress verbose PyMongo logs (but cannot suppress MongoDB server logs)
# Set pymongo logger to WARNING to reduce noise from driver-level logs
pymongo_logger = logging.getLogger('pymongo')
pymongo_logger.setLevel(logging.WARNING)

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
    
    # Attempt connection with optimized settings for Railway
    try:
        client = MongoClient(
            MONGO_URL,
            serverSelectionTimeoutMS=5000,  # 5s timeout for server selection
            connectTimeoutMS=5000,  # 5s timeout for initial connection
            socketTimeoutMS=30000,  # 30s timeout for operations
            maxPoolSize=10,  # Connection pool size (reasonable for Railway)
            minPoolSize=0,   # Don't maintain idle connections (saves resources)
            maxIdleTimeMS=30000,  # Close idle connections after 30s (handles Railway idle timeout)
            waitQueueTimeoutMS=10000,  # Wait up to 10s for available connection
            retryWrites=True,  # Retry writes on network errors (auto-reconnect)
            retryReads=True,   # Retry reads on network errors (auto-reconnect)
            # Compression: Use zlib (built-in, no extra dependencies)
            # This reduces network traffic and can help with log costs
            compressors=['zlib'],
            zlibCompressionLevel=1  # Fast compression (speed over ratio)
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


def save_article(article_id: str, content: str) -> bool:
    """Save article content to MongoDB.
    
    This function updates only the content and status fields.
    Metadata fields (language, level, length, topic) are immutable
    after article creation and should not be updated here.
    
    Args:
        article_id: Unique article identifier
        content: Markdown content (includes all information: title, source, URL, date, author, body)
        
    Returns:
        True if successful, False otherwise
    """
    client = get_mongodb_client()
    if not client:
        return False
    
    try:
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        # Only update content and status, not metadata
        # Metadata (language, level, length, topic) was set during article creation
        # and should remain immutable
        update_data = {
            'content': content,
            'status': 'completed',
            'updated_at': datetime.utcnow()
        }
        
        result = collection.update_one(
            {'_id': article_id},
            {'$set': update_data}
        )
        
        # Check if article actually exists and was updated
        # If matched_count is 0, the article doesn't exist in MongoDB
        if result.matched_count == 0:
            logger.error("Article not found in MongoDB. Cannot save content.", extra={"articleId": article_id})
            return False
        
        logger.info("Article content saved to MongoDB", extra={"articleId": article_id})
        return True
    except PyMongoError as e:
        logger.error("Failed to save article", extra={"articleId": article_id, "error": str(e)})
        return False


def get_article(article_id: str) -> Optional[dict]:
    """Get article from MongoDB.
    
    Args:
        article_id: Article identifier
        
    Returns:
        Article document (with content) or None if not found.
        Note: Returns None for both "article not found" and "MongoDB connection failed".
        Callers should check get_mongodb_client() separately to distinguish these cases.
    """
    client = get_mongodb_client()
    if not client:
        # MongoDB connection failed - return None
        # Caller should check get_mongodb_client() to distinguish from "not found"
        return None
    
    try:
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        article = collection.find_one({'_id': article_id})
        return article  # None if not found, dict if found
    except PyMongoError as e:
        logger.error("Failed to get article", extra={"articleId": article_id, "error": str(e)})
        # Database error during query - treat as connection failure
        return None


def save_article_metadata(article_id: str, language: str, level: str, 
                          length: str, topic: str, status: str = 'pending',
                          created_at: Optional[datetime] = None,
                          owner_id: Optional[str] = None) -> bool:
    """Save article metadata to MongoDB (without content).
    
    Used when creating article before generation starts.
    
    Args:
        article_id: Unique article identifier
        language: Target language
        level: Language level (A1-C2)
        length: Target word count
        topic: Article topic
        status: Article status (default: 'pending')
        created_at: Optional timestamp for created_at field. If None, uses current UTC time.
                    This allows the caller to control the timestamp and avoid race conditions.
                    By passing created_at from the caller, we eliminate the need to fetch
                    the saved document immediately after saving, preventing orphaned records
                    if MongoDB becomes unavailable between save and fetch operations.
        owner_id: Optional owner ID for multi-user support
        
    Returns:
        True if successful, False otherwise
    """
    client = get_mongodb_client()
    if not client:
        return False
    
    try:
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        # Use provided created_at or current time
        if created_at is None:
            created_at = datetime.utcnow()
        
        # Build inputs object (structured parameters)
        inputs = {
            'language': language,
            'level': level,
            'length': length,
            'topic': topic
        }
        
        article_doc = {
            '_id': article_id,
            # Keep existing fields for backward compatibility
            'language': language,
            'level': level,
            'length': length,
            'topic': topic,
            # New structured field
            'inputs': inputs,
            'status': status,
            'updated_at': datetime.utcnow()
        }
        
        # Add optional fields if provided
        if owner_id is not None:
            article_doc['owner_id'] = owner_id
        
        # Use upsert to handle both insert and update
        # $setOnInsert only sets created_at on insert, not on update
        collection.update_one(
            {'_id': article_id},
            {
                '$set': article_doc,
                '$setOnInsert': {'created_at': created_at}
            },
            upsert=True
        )
        
        logger.info("Article metadata saved to MongoDB", extra={"articleId": article_id})
        return True
    except PyMongoError as e:
        logger.error("Failed to save article metadata", extra={"articleId": article_id, "error": str(e)})
        return False


def get_latest_article() -> Optional[dict]:
    """Get the most recently created article.
    
    Returns:
        Article document with all fields or None if no articles exist
    """
    client = get_mongodb_client()
    if not client:
        return None
    
    try:
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        # Find the most recent article by created_at
        article = collection.find_one(
            {},
            sort=[('created_at', -1)]  # Sort by created_at descending (newest first)
        )
        
        if article:
            article_id = article.get('_id')
            logger.debug("Found latest article", extra={"articleId": article_id})
        else:
            logger.debug("No articles found in database")
        
        return article
    except (ConnectionFailure, PyMongoError) as e:
        logger.error("Failed to get latest article", extra={"error": str(e)})
        # Clear cache to force reconnection on next call
        global _client_cache
        _client_cache = None
        return None
