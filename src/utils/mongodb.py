"""MongoDB utilities for article storage."""

import os
import logging
import uuid
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
VOCABULARY_COLLECTION_NAME = 'vocabularies'
USERS_COLLECTION_NAME = 'users'

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
        # Note: Use 'completed' status for MongoDB (matches existing data)
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
                          length: str, topic: str, status: str = 'running',
                          created_at: Optional[datetime] = None,
                          user_id: Optional[str] = None,
                          job_id: Optional[str] = None) -> bool:
    """Save article metadata to MongoDB (without content).
    
    Used when creating article before generation starts.
    
    Args:
        article_id: Unique article identifier
        language: Target language
        level: Language level (A1-C2)
        length: Target word count
        topic: Article topic
        status: Article status (default: 'running')
        created_at: Optional timestamp for created_at field. If None, uses current UTC time.
                    This allows the caller to control the timestamp and avoid race conditions.
                    By passing created_at from the caller, we eliminate the need to fetch
                    the saved document immediately after saving, preventing orphaned records
                    if MongoDB becomes unavailable between save and fetch operations.
        user_id: Optional owner ID for multi-user support
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
            'user_id': user_id,
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


def _ensure_articles_indexes() -> bool:
    """Ensure MongoDB indexes exist for articles collection.
    
    Creates indexes if they don't exist:
    - created_at: descending (for get_latest_article queries)
    - user_id: ascending, sparse (for future multi-user queries)
    - compound index: user_id + inputs.* + created_at (for duplicate detection)
    
    This function is idempotent - safe to call multiple times.
    Handles index name conflicts by removing old indexes with different names.
    
    Returns:
        True if indexes were created/verified successfully, False otherwise
    """
    client = get_mongodb_client()
    if not client:
        return False
    
    try:
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        # Helper function to ensure index with conflict handling
        def _ensure_index(keys, name, **kwargs):
            """Create index, removing conflicting indexes if needed."""
            try:
                # Try to create index with the desired name
                collection.create_index(keys, name=name, **kwargs)
                logger.info(f"Created/verified index: {name}")
            except PyMongoError as e:
                error_str = str(e)
                # Check if error is due to index conflict (name or key spec mismatch)
                if any(conflict in error_str for conflict in [
                    'Index already exists with a different name',
                    'IndexOptionsConflict',
                    'IndexKeySpecsConflict'  # Index name same but keys different (e.g., owner_id -> user_id)
                ]):
                    # Find and drop conflicting index
                    # Get all existing indexes
                    existing_indexes = list(collection.list_indexes())
                    keys_dict = dict(keys)  # Convert list of tuples to dict for comparison

                    for idx in existing_indexes:
                        idx_name = idx.get('name')
                        idx_keys = idx.get('key', {})

                        # Skip _id index
                        if idx_name == '_id_':
                            continue

                        # Check if this index has the target name (regardless of keys)
                        # This handles schema migrations where field names change (e.g., owner_id -> user_id)
                        if idx_name == name:
                            # Check if keys are different
                            if isinstance(idx_keys, dict) and keys_dict != idx_keys:
                                logger.warning(
                                    f"Dropping index with same name but different keys: {idx_name} "
                                    f"(old keys: {idx_keys}, new keys: {keys_dict})"
                                )
                                try:
                                    collection.drop_index(idx_name)
                                    # Retry creating index with new key specification
                                    collection.create_index(keys, name=name, **kwargs)
                                    logger.info(f"Created index: {name} with updated key specification")
                                    return
                                except PyMongoError as drop_error:
                                    logger.error(f"Failed to drop conflicting index {idx_name}", extra={"error": str(drop_error)})
                                    raise

                        # Check if keys match but name is different
                        elif isinstance(idx_keys, dict) and keys_dict == idx_keys:
                            logger.warning(f"Dropping conflicting index: {idx_name} (replacing with {name})")
                            try:
                                collection.drop_index(idx_name)
                                # Retry creating index with desired name
                                collection.create_index(keys, name=name, **kwargs)
                                logger.info(f"Created index: {name} (replaced {idx_name})")
                                return
                            except PyMongoError as drop_error:
                                logger.error(f"Failed to drop conflicting index {idx_name}", extra={"error": str(drop_error)})
                                raise

                    # If we get here, couldn't resolve conflict
                    logger.error(f"Failed to resolve index conflict for {name}", extra={"error": error_str})
                    raise
                else:
                    # Other error, re-raise
                    raise
        
        # Create index on created_at (descending) for latest article queries
        _ensure_index([('created_at', -1)], 'idx_created_at_desc')
        
        # Create sparse index on user_id (for future multi-user support)
        # Sparse index only includes documents that have the user_id field
        _ensure_index([('user_id', 1)], 'idx_user_id', sparse=True)
        
        # Create compound index for duplicate detection
        # This enables efficient queries on: user_id + inputs.* + created_at
        # Used by find_duplicate_article() for O(log N) duplicate detection
        _ensure_index([
            ('user_id', 1),
            ('inputs.language', 1),
            ('inputs.level', 1),
            ('inputs.length', 1),
            ('inputs.topic', 1),
            ('created_at', -1)
        ], 'idx_duplicate_detection')
        
        return True
    except PyMongoError as e:
        logger.error("Failed to create articles indexes", extra={"error": str(e)})
        return False


def _ensure_users_indexes() -> bool:
    """Ensure MongoDB indexes exist for users collection.
    
    Creates indexes if they don't exist:
    - email: unique index (for login and duplicate prevention)
    - created_at: descending index (for latest users queries)
    
    This function is idempotent - safe to call multiple times.
    Handles index name conflicts by removing old indexes with different names.
    
    Returns:
        True if indexes were created/verified successfully, False otherwise
    """
    client = get_mongodb_client()
    if not client:
        return False
    
    try:
        db = client[DATABASE_NAME]
        collection = db[USERS_COLLECTION_NAME]
        
        # Helper function to ensure index with conflict handling
        def _ensure_index(keys, name, **kwargs):
            """Create index, removing conflicting indexes if needed."""
            try:
                # Try to create index with the desired name
                collection.create_index(keys, name=name, **kwargs)
                logger.info(f"Created/verified index: {name}")
            except PyMongoError as e:
                error_str = str(e)
                # Check if error is due to index conflict (name or key spec mismatch)
                if any(conflict in error_str for conflict in [
                    'Index already exists with a different name',
                    'IndexOptionsConflict',
                    'IndexKeySpecsConflict'  # Index name same but keys different (e.g., owner_id -> user_id)
                ]):
                    # Find and drop conflicting index
                    # Get all existing indexes
                    existing_indexes = list(collection.list_indexes())
                    keys_dict = dict(keys)  # Convert list of tuples to dict for comparison

                    for idx in existing_indexes:
                        idx_name = idx.get('name')
                        idx_keys = idx.get('key', {})

                        # Skip _id index
                        if idx_name == '_id_':
                            continue

                        # Check if this index has the target name (regardless of keys)
                        # This handles schema migrations where field names change (e.g., owner_id -> user_id)
                        if idx_name == name:
                            # Check if keys are different
                            if isinstance(idx_keys, dict) and keys_dict != idx_keys:
                                logger.warning(
                                    f"Dropping index with same name but different keys: {idx_name} "
                                    f"(old keys: {idx_keys}, new keys: {keys_dict})"
                                )
                                try:
                                    collection.drop_index(idx_name)
                                    # Retry creating index with new key specification
                                    collection.create_index(keys, name=name, **kwargs)
                                    logger.info(f"Created index: {name} with updated key specification")
                                    return
                                except PyMongoError as drop_error:
                                    logger.error(f"Failed to drop conflicting index {idx_name}", extra={"error": str(drop_error)})
                                    raise

                        # Check if keys match but name is different
                        elif isinstance(idx_keys, dict) and keys_dict == idx_keys:
                            logger.warning(f"Dropping conflicting index: {idx_name} (replacing with {name})")
                            try:
                                collection.drop_index(idx_name)
                                # Retry creating index with desired name
                                collection.create_index(keys, name=name, **kwargs)
                                logger.info(f"Created index: {name} (replaced {idx_name})")
                                return
                            except PyMongoError as drop_error:
                                logger.error(f"Failed to drop conflicting index {idx_name}", extra={"error": str(drop_error)})
                                raise

                    # If we get here, couldn't resolve conflict
                    logger.error(f"Failed to resolve index conflict for {name}", extra={"error": error_str})
                    raise
                else:
                    # Other error, re-raise
                    raise
        
        # Create unique index on email (for login and duplicate prevention)
        _ensure_index([('email', 1)], 'idx_users_email', unique=True)
        
        # Create index on created_at (descending) for latest users queries
        _ensure_index([('created_at', -1)], 'idx_users_created_at')
        
        return True
    except PyMongoError as e:
        logger.error("Failed to create users indexes", extra={"error": str(e)})
        return False


def ensure_indexes() -> bool:
    """Ensure all MongoDB indexes exist for all collections.
    
    This function is idempotent - safe to call multiple times.
    
    Returns:
        True if all indexes were created/verified successfully, False otherwise
    """
    articles_ok = _ensure_articles_indexes()
    users_ok = _ensure_users_indexes()
    return articles_ok and users_ok


def find_duplicate_article(inputs: dict, user_id: Optional[str] = None, hours: int = 24) -> Optional[dict]:
    """Find duplicate article by inputs within specified hours.
    
    Searches for articles with identical inputs created within the time window.
    Used for duplicate detection before creating new articles.
    
    Args:
        inputs: Article inputs dict with keys: language, level, length, topic
        user_id: Owner ID for user-specific search (None for anonymous)
        hours: Time window in hours (default: 24)
        
    Returns:
        Article document if duplicate found, None otherwise
        
    Performance:
        Uses compound index on (user_id, inputs.*, created_at) for O(log N) lookup
    """
    client = get_mongodb_client()
    if not client:
        return None
    
    try:
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        # Calculate cutoff time
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Build query: exact inputs match + user_id + recent created_at
        query = {
            'inputs': inputs,  # Exact match on nested dict
            'created_at': {'$gte': cutoff},
            'user_id': user_id  # None matches None (anonymous users)
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
                "userId": user_id,
                "inputs": inputs
            })
        
        return article
    except (ConnectionFailure, PyMongoError) as e:
        logger.error("Failed to find duplicate article", extra={
            "error": str(e),
            "userId": user_id
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
    user_id: Optional[str] = None,
    exclude_deleted: bool = True
) -> tuple[list[dict], int]:
    """List articles with filtering, sorting, and pagination.
    
    Args:
        skip: Number of articles to skip (for pagination)
        limit: Maximum number of articles to return
        status: Filter by status (e.g., 'running', 'completed', 'deleted')
        language: Filter by language
        level: Filter by level
        user_id: Filter by user_id
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
        if user_id:
            filter_query['user_id'] = user_id
        
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


def update_article_status(article_id: str, status: str) -> bool:
    """Update article status in MongoDB.
    
    Used to update article status during job processing:
    - 'running' → 'completed' (when job completes successfully)
    - 'running' → 'failed' (when job fails)
    - 'running' → 'deleted' (when article is soft deleted)
    
    Args:
        article_id: Article ID to update
        status: New status ('running', 'completed', 'failed', 'deleted')
    
    Returns:
        True if successful, False otherwise
    """
    client = get_mongodb_client()
    if not client:
        return False
    
    try:
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        result = collection.update_one(
            {'_id': article_id},
            {
                '$set': {
                    'status': status,
                    'updated_at': datetime.now(timezone.utc)
                }
            }
        )
        
        if result.matched_count == 0:
            logger.warning("Article not found for status update", extra={"articleId": article_id, "status": status})
            return False
        
        logger.debug("Article status updated", extra={"articleId": article_id, "status": status})
        return True
    except PyMongoError as e:
        logger.error("Failed to update article status", extra={"articleId": article_id, "status": status, "error": str(e)})
        return False


def delete_article(article_id: str) -> bool:
    """Soft delete article by setting status='deleted'.
    
    Soft delete preserves data for potential recovery and audit trail.
    Article remains in database but is marked as deleted.
    
    Args:
        article_id: Article ID to delete
    
    Returns:
        True if successful, False otherwise
    """
    client = get_mongodb_client()
    if not client:
        return False
    
    try:
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        # Soft delete: set status='deleted'
        result = collection.update_one(
            {'_id': article_id},
            {
                '$set': {
                    'status': 'deleted',
                    'updated_at': datetime.now(timezone.utc)
                }
            }
        )
        
        if result.matched_count == 0:
            logger.warning("Article not found for deletion", extra={"articleId": article_id})
            return False
        
        logger.info("Article soft deleted", extra={"articleId": article_id})
        return True
    except PyMongoError as e:
        logger.error("Failed to delete article", extra={"articleId": article_id, "error": str(e)})
        return False


def save_vocabulary(
    article_id: str,
    word: str,
    lemma: str,
    definition: str,
    sentence: str,
    language: str,
    related_words: list[str] | None = None,
    span_id: str | None = None
) -> str | None:
    """Save vocabulary word to MongoDB.
    
    Args:
        article_id: Article ID where the word was found
        word: Original word clicked
        lemma: Dictionary form (lemma)
        definition: Word definition
        sentence: Sentence context
        language: Language
        related_words: All words in sentence belonging to this lemma (e.g., for separable verbs)
        span_id: Span ID of the clicked word
        
    Returns:
        Vocabulary ID if successful, None otherwise
    """
    client = get_mongodb_client()
    if not client:
        return None
    
    try:
        db = client[DATABASE_NAME]
        collection = db[VOCABULARY_COLLECTION_NAME]
        
        # Check if vocabulary already exists (same article_id and lemma)
        existing = collection.find_one({
            'article_id': article_id,
            'lemma': lemma.lower()
        })
        
        # Normalize span_id: convert empty string to None
        normalized_span_id = span_id if span_id and span_id.strip() else None
        
        if existing:
            # Update span_id if provided and different
            if normalized_span_id and existing.get('span_id') != normalized_span_id:
                collection.update_one(
                    {'_id': existing['_id']},
                    {'$set': {'span_id': normalized_span_id, 'updated_at': datetime.now(timezone.utc)}}
                )
            # Return existing vocabulary ID
            return existing['_id']
        
        # Create new vocabulary
        vocabulary_doc = {
            '_id': str(uuid.uuid4()),
            'article_id': article_id,
            'word': word,
            'lemma': lemma.lower(),  # Store lowercase for case-insensitive lookup
            'definition': definition,
            'sentence': sentence,
            'language': language,
            'related_words': [w.lower() for w in (related_words or [])],  # Store lowercase for case-insensitive lookup
            'span_id': normalized_span_id,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        
        collection.insert_one(vocabulary_doc)
        vocabulary_id = vocabulary_doc['_id']
        
        logger.info("Vocabulary saved", extra={
            "vocabularyId": vocabulary_id,
            "articleId": article_id,
            "lemma": lemma
        })
        return vocabulary_id
    except PyMongoError as e:
        logger.error("Failed to save vocabulary", extra={
            "articleId": article_id,
            "lemma": lemma,
            "error": str(e)
        })
        return None


def get_vocabularies(article_id: str | None = None) -> list[dict]:
    """Get vocabularies from MongoDB.
    
    Args:
        article_id: Optional article ID to filter by
        
    Returns:
        List of vocabulary documents
    """
    client = get_mongodb_client()
    if not client:
        return []
    
    try:
        db = client[DATABASE_NAME]
        collection = db[VOCABULARY_COLLECTION_NAME]
        
        query = {}
        if article_id:
            query['article_id'] = article_id
        
        # Convert ObjectId to string and format for API response
        result = []
        for vocab in collection.find(query).sort('created_at', -1):
            result.append({
                'id': vocab['_id'],
                'article_id': vocab['article_id'],
                'word': vocab['word'],
                'lemma': vocab['lemma'],
                'definition': vocab['definition'],
                'sentence': vocab['sentence'],
                'span_id': vocab.get('span_id'),  # Include span_id in response
                'language': vocab['language'],
                'related_words': vocab.get('related_words', None),  # May not exist for old entries
                'created_at': vocab['created_at']
            })
        
        return result
    except PyMongoError as e:
        logger.error("Failed to get vocabularies", extra={
            "articleId": article_id,
            "error": str(e)
        })
        return []


def delete_vocabulary(vocabulary_id: str) -> bool:
    """Delete vocabulary from MongoDB.
    
    Args:
        vocabulary_id: Vocabulary ID to delete
        
    Returns:
        True if successful, False otherwise
    """
    client = get_mongodb_client()
    if not client:
        return False
    
    try:
        db = client[DATABASE_NAME]
        collection = db[VOCABULARY_COLLECTION_NAME]
        
        result = collection.delete_one({'_id': vocabulary_id})
        
        if result.deleted_count == 0:
            logger.warning("Vocabulary not found for deletion", extra={"vocabularyId": vocabulary_id})
            return False
        
        logger.info("Vocabulary deleted", extra={"vocabularyId": vocabulary_id})
        return True
    except PyMongoError as e:
        logger.error("Failed to delete vocabulary", extra={
            "vocabularyId": vocabulary_id,
            "error": str(e)
        })
        return False


def get_database_stats() -> Optional[dict]:
    """Get MongoDB database and collection statistics.
    
    Returns information about:
    - Collection size (dataSize)
    - Index size (indexSize)
    - Total size (totalSize)
    - Document count
    - Average document size
    
    Returns:
        Dictionary with statistics or None if unavailable
    """
    client = get_mongodb_client()
    if not client:
        return None
    
    try:
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        # Get collection stats
        coll_stats = db.command("collStats", COLLECTION_NAME)
        
        # Get document count by status
        total_count = collection.count_documents({})
        deleted_count = collection.count_documents({'status': 'deleted'})
        running_count = collection.count_documents({'status': 'running'})
        failed_count = collection.count_documents({'status': 'failed'})
        completed_count = collection.count_documents({'status': 'completed'})
        active_count = total_count - deleted_count
        
        # Format sizes in MB
        # 'size': Uncompressed document data size in memory (bytes) - includes padding
        # 'storageSize': Allocated disk space for collection data (bytes) - compressed, includes free space
        # 'totalIndexSize': Total size of all indexes (bytes)
        # 'totalSize': storageSize + totalIndexSize (actual disk usage)
        data_size_bytes = coll_stats.get('size', 0)
        index_size_bytes = coll_stats.get('totalIndexSize', 0)
        storage_size_bytes = coll_stats.get('storageSize', 0)
        total_size_bytes = coll_stats.get('totalSize', storage_size_bytes + index_size_bytes)
        
        data_size_mb = data_size_bytes / (1024 * 1024)
        index_size_mb = index_size_bytes / (1024 * 1024)
        storage_size_mb = storage_size_bytes / (1024 * 1024)
        total_size_mb = total_size_bytes / (1024 * 1024)
        
        result = {
            'total_documents': total_count,
            'active_documents': active_count,
            'deleted_documents': deleted_count,
            'running_documents': running_count,
            'failed_documents': failed_count,
            'completed_documents': completed_count,
            'data_size_mb': round(data_size_mb, 2),
            'data_size_bytes': data_size_bytes,
            'index_size_mb': round(index_size_mb, 2),
            'index_size_bytes': index_size_bytes,
            'storage_size_mb': round(storage_size_mb, 2),
            'storage_size_bytes': storage_size_bytes,
            'total_size_mb': round(total_size_mb, 2),
            'total_size_bytes': total_size_bytes,
            'avg_document_size_bytes': round(coll_stats.get('avgObjSize', 0), 2),
        }
        
        logger.info("Database statistics retrieved", extra={
            "totalDocuments": total_count,
            "dataSizeMB": round(data_size_mb, 2),
            "indexSizeMB": round(index_size_mb, 2)
        })
        
        return result
    except PyMongoError as e:
        logger.error("Failed to get database stats", extra={"error": str(e)})
        return None


def get_vocabulary_stats() -> Optional[dict]:
    """Get vocabulary collection statistics.
    
    Returns information about:
    - Collection size (dataSize)
    - Index size (indexSize)
    - Total size (totalSize)
    - Document count
    - Average document size
    - Count by language
    
    Returns:
        Dictionary with vocabulary statistics or None if unavailable
    """
    client = get_mongodb_client()
    if not client:
        return None
    
    try:
        db = client[DATABASE_NAME]
        collection = db[VOCABULARY_COLLECTION_NAME]
        
        # Get collection stats
        coll_stats = db.command("collStats", VOCABULARY_COLLECTION_NAME)
        
        # Get document count
        total_count = collection.count_documents({})
        
        # Get count by language using aggregation
        language_counts = {}
        for doc in collection.aggregate([
            {'$group': {'_id': '$language', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]):
            lang = doc.get('_id') or 'Unknown'
            language_counts[lang] = doc.get('count', 0)
        
        # Format sizes in MB
        data_size_bytes = coll_stats.get('size', 0)
        index_size_bytes = coll_stats.get('totalIndexSize', 0)
        storage_size_bytes = coll_stats.get('storageSize', 0)
        total_size_bytes = coll_stats.get('totalSize', storage_size_bytes + index_size_bytes)
        
        data_size_mb = data_size_bytes / (1024 * 1024)
        index_size_mb = index_size_bytes / (1024 * 1024)
        storage_size_mb = storage_size_bytes / (1024 * 1024)
        total_size_mb = total_size_bytes / (1024 * 1024)
        
        result = {
            'total_documents': total_count,
            'data_size_mb': round(data_size_mb, 2),
            'data_size_bytes': data_size_bytes,
            'index_size_mb': round(index_size_mb, 2),
            'index_size_bytes': index_size_bytes,
            'storage_size_mb': round(storage_size_mb, 2),
            'storage_size_bytes': storage_size_bytes,
            'total_size_mb': round(total_size_mb, 2),
            'total_size_bytes': total_size_bytes,
            'avg_document_size_bytes': round(coll_stats.get('avgObjSize', 0), 2),
            'by_language': language_counts,
        }
        
        logger.info("Vocabulary statistics retrieved", extra={
            "totalDocuments": total_count,
            "dataSizeMB": round(data_size_mb, 2)
        })
        
        return result
    except PyMongoError as e:
        logger.error("Failed to get vocabulary stats", extra={"error": str(e)})
        return None


def get_vocabulary_word_counts(language: str | None = None) -> list[dict]:
    """Get vocabulary word counts grouped by language and lemma.
    
    Args:
        language: Optional language filter
        
    Returns:
        List of dictionaries with language, lemma, count, and article_ids:
        [
            {'language': 'English', 'lemma': 'agent', 'count': 5, 'article_ids': ['id1', 'id2']},
            ...
        ]
    """
    client = get_mongodb_client()
    if not client:
        return []
    
    try:
        db = client[DATABASE_NAME]
        collection = db[VOCABULARY_COLLECTION_NAME]
        
        # Build aggregation pipeline
        pipeline = []
        
        # Filter by language if provided
        if language:
            pipeline.append({'$match': {'language': language}})
        
        # Group by language and lemma
        pipeline.extend([
            {
                '$group': {
                    '_id': {
                        'language': '$language',
                        'lemma': '$lemma'
                    },
                    'count': {'$sum': 1},
                    'article_ids': {'$addToSet': '$article_id'}
                }
            },
            {
                '$sort': {'count': -1, '_id.lemma': 1}
            }
        ])
        
        result = []
        for doc in collection.aggregate(pipeline):
            result.append({
                'language': doc['_id']['language'],
                'lemma': doc['_id']['lemma'],
                'count': doc['count'],
                'article_ids': doc['article_ids']
            })
        
        return result
    except PyMongoError as e:
        logger.error("Failed to get vocabulary word counts", extra={"error": str(e)})
        return []


# ============================================================================
# Users Collection Functions
# ============================================================================

def get_user(email: str) -> dict | None:
    """Get user by email from MongoDB.
    
    Args:
        email: User email address
        
    Returns:
        User document or None if not found
    """
    client = get_mongodb_client()
    if not client:
        return None
    
    try:
        db = client[DATABASE_NAME]
        collection = db[USERS_COLLECTION_NAME]
        
        user = collection.find_one({'email': email})
        if user:
            # Convert _id to string for consistency
            user['id'] = user.pop('_id')
            return user
        return None
    except PyMongoError as e:
        logger.error("Failed to get user by email", extra={"email": email, "error": str(e)})
        return None


def create_user(email: str, password_hash: str, name: str) -> dict | None:
    """Create a new user in MongoDB.
    
    Args:
        email: User email address (must be unique)
        password_hash: Bcrypt hashed password
        name: Display name
        
    Returns:
        Created user document or None if creation failed
        
    Raises:
        PyMongoError: If email already exists or database error occurs
    """
    client = get_mongodb_client()
    if not client:
        return None
    
    try:
        db = client[DATABASE_NAME]
        collection = db[USERS_COLLECTION_NAME]
        
        # Generate user ID (UUID)
        user_id = uuid.uuid4().hex
        
        # Create user document
        now = datetime.now(timezone.utc)
        user_doc = {
            '_id': user_id,
            'email': email,
            'password_hash': password_hash,
            'name': name,
            'created_at': now,
            'updated_at': now,
            'provider': 'email'
        }
        
        collection.insert_one(user_doc)
        
        # Convert _id to id for consistency
        user_doc['id'] = user_doc.pop('_id')
        
        logger.info("User created", extra={"userId": user_id, "email": email})
        return user_doc
    except PyMongoError as e:
        error_str = str(e)
        if 'duplicate key' in error_str.lower() or 'E11000' in error_str:
            logger.warning("User creation failed: email already exists", extra={"email": email})
        else:
            logger.error("Failed to create user", extra={"email": email, "error": error_str})
        return None


def get_user_by_id(user_id: str) -> dict | None:
    """Get user by ID from MongoDB.
    
    Args:
        user_id: User ID (MongoDB _id)
        
    Returns:
        User document or None if not found
    """
    client = get_mongodb_client()
    if not client:
        return None
    
    try:
        db = client[DATABASE_NAME]
        collection = db[USERS_COLLECTION_NAME]
        
        user = collection.find_one({'_id': user_id})
        if user:
            # Convert _id to string for consistency
            user['id'] = user.pop('_id')
            return user
        return None
    except PyMongoError as e:
        logger.error("Failed to get user by ID", extra={"userId": user_id, "error": str(e)})
        return None