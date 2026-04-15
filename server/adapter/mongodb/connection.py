import os
import logging
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
TOKEN_USAGE_COLLECTION_NAME = 'token_usage'

_client_cache = None
_connection_attempted = False
_connection_failed = False


def reset_client():
    global _client_cache
    _client_cache = None
    

def get_mongodb_client() -> MongoClient | None:
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
        except Exception:
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