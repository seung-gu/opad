"""MongoDB utilities for article storage."""

import os
import logging
from typing import Optional
from datetime import datetime, timedelta, timezone
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
            'updated_at': datetime.now(timezone.utc)
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
                          owner_id: Optional[str] = None,
                          job_id: Optional[str] = None) -> bool:
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
        job_id: Optional job ID for tracking generation job
        
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
            created_at = datetime.now(timezone.utc)
        
        # Build inputs object (structured parameters)
        inputs = {
            'language': language,
            'level': level,
            'length': length,
            'topic': topic
        }
        
        # Build update document (exclude _id - it's immutable and only used in query filter)
        article_doc = {
            'inputs': inputs,  # Store only inputs (structured)
            'status': status,
            'updated_at': datetime.now(timezone.utc),
            'owner_id': owner_id,
            'job_id': job_id  # Store job_id for duplicate detection
        }
        
        # Use upsert to handle both insert and update
        # $setOnInsert only sets created_at on insert, not on update
        # Note: _id is only used in query filter, not in $set (MongoDB _id is immutable)
        collection.update_one(
            {'_id': article_id},
            {
                '$set': article_doc,
                '$setOnInsert': {'created_at': created_at, '_id': article_id}
            },
            upsert=True
        )
        
        logger.info("Article metadata saved to MongoDB", extra={"articleId": article_id, "jobId": job_id})
        return True
    except PyMongoError as e:
        logger.error("Failed to save article metadata", extra={"articleId": article_id, "error": str(e)})
        return False


def ensure_indexes() -> bool:
    """Ensure MongoDB indexes exist for articles collection.
    
    Creates indexes if they don't exist:
    - created_at: descending (for get_latest_article queries)
    - owner_id: ascending, sparse (for future multi-user queries)
    - compound index: owner_id + inputs.* + created_at (for duplicate detection)
    
    This function is idempotent - safe to call multiple times.
    MongoDB will skip index creation if the index already exists.
    
    Returns:
        True if indexes were created/verified successfully, False otherwise
    """
    client = get_mongodb_client()
    if not client:
        return False
    
    try:
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        # Create index on created_at (descending) for latest article queries
        collection.create_index([('created_at', -1)])
        logger.info("Created index on created_at (descending)")
        
        # Create sparse index on owner_id (for future multi-user support)
        # Sparse index only includes documents that have the owner_id field
        collection.create_index([('owner_id', 1)], sparse=True)
        logger.info("Created sparse index on owner_id")
        
        # Create compound index for duplicate detection
        # This enables efficient queries on: owner_id + inputs.* + created_at
        # Used by find_duplicate_article() for O(log N) duplicate detection
        collection.create_index([
            ('owner_id', 1),
            ('inputs.language', 1),
            ('inputs.level', 1),
            ('inputs.length', 1),
            ('inputs.topic', 1),
            ('created_at', -1)
        ])
        logger.info("Created compound index for duplicate detection (owner_id + inputs + created_at)")
        
        return True
    except PyMongoError as e:
        logger.error("Failed to create indexes", extra={"error": str(e)})
        return False


def find_duplicate_article(inputs: dict, owner_id: Optional[str] = None, hours: int = 24) -> Optional[dict]:
    """Find duplicate article by inputs within specified hours.
    
    Searches for articles with identical inputs created within the time window.
    Used for duplicate detection before creating new articles.
    
    Args:
        inputs: Article inputs dict with keys: language, level, length, topic
        owner_id: Owner ID for user-specific search (None for anonymous)
        hours: Time window in hours (default: 24)
        
    Returns:
        Article document if duplicate found, None otherwise
        
    Performance:
        Uses compound index on (owner_id, inputs.*, created_at) for O(log N) lookup
    """
    client = get_mongodb_client()
    if not client:
        return None
    
    try:
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        # Calculate cutoff time
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Build query: exact inputs match + owner_id + recent created_at
        query = {
            'inputs': inputs,  # Exact match on nested dict
            'created_at': {'$gte': cutoff},
            'owner_id': owner_id  # None matches None (anonymous users)
        }
        
        # Find most recent matching article
        article = collection.find_one(
            query,
            sort=[('created_at', -1)]  # Most recent first
        )
        
        if article:
            article_id = article.get('_id')
            logger.debug("Found duplicate article", extra={
                "articleId": article_id,
                "ownerId": owner_id,
                "inputs": inputs
            })
        
        return article
    except (ConnectionFailure, PyMongoError) as e:
        logger.error("Failed to find duplicate article", extra={
            "error": str(e),
            "ownerId": owner_id
        })
        # Clear cache to force reconnection on next call
        global _client_cache
        _client_cache = None
        return None


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


def list_articles(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    language: Optional[str] = None,
    level: Optional[str] = None,
    owner_id: Optional[str] = None,
    exclude_deleted: bool = True
) -> tuple[list[dict], int]:
    """List articles with filtering, sorting, and pagination.
    
    Args:
        skip: Number of articles to skip (for pagination)
        limit: Maximum number of articles to return
        status: Filter by status (e.g., 'pending', 'succeeded', 'deleted')
        language: Filter by language
        level: Filter by level
        owner_id: Filter by owner_id
        exclude_deleted: If True (default), exclude soft-deleted articles (status='deleted')
                        unless status='deleted' is explicitly requested
    
    Returns:
        (articles, total_count) tuple
        - articles: List of article documents
        - total_count: Total number of articles matching filters
    """
    client = get_mongodb_client()
    if not client:
        return [], 0
    
    try:
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        # Build filter query
        filter_query = {}
        if status:
            filter_query['status'] = status
        elif exclude_deleted:
            # By default, exclude soft-deleted articles unless status is explicitly set
            filter_query['status'] = {'$ne': 'deleted'}
        if language:
            filter_query['inputs.language'] = language
        if level:
            filter_query['inputs.level'] = level
        if owner_id:
            filter_query['owner_id'] = owner_id
        
        # Get total count for pagination
        total_count = collection.count_documents(filter_query)
        
        # Get articles with sorting and pagination
        articles = list(collection.find(filter_query)
                       .sort('created_at', -1)  # Newest first
                       .skip(skip)
                       .limit(limit))
        
        logger.info("Listed articles", extra={
            "count": len(articles),
            "total": total_count,
            "skip": skip,
            "limit": limit,
            "filters": filter_query
        })
        
        return articles, total_count
    except PyMongoError as e:
        logger.error("Failed to list articles", extra={"error": str(e)})
        return [], 0
