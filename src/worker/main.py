"""Worker service entry point."""

#!/usr/bin/env python
import sys
import logging
from pathlib import Path

# Add src to path
# main.py is at /app/src/worker/main.py
# src is at /app/src, so we go up 2 levels (same as processor.py)
sys.path.insert(0, str(Path(__file__).parent.parent))

from worker.processor import run_worker_loop
from utils.logging import setup_structured_logging
from adapter.mongodb.article_repository import MongoArticleRepository
from adapter.mongodb.token_usage_repository import MongoTokenUsageRepository
from adapter.mongodb.vocabulary_repository import MongoVocabularyRepository
from adapter.mongodb.connection import get_mongodb_client, DATABASE_NAME
from adapter.external.litellm import LiteLLMAdapter

# Set up structured JSON logging
setup_structured_logging()

logger = logging.getLogger(__name__)


def main():
    """Main entry point for worker service."""
    logger.info("Starting OPAD Worker service...")
    logger.info("This service consumes jobs from Redis queue and executes CrewAI")

    try:
        client = get_mongodb_client()
        if client is None:
            logger.error("Cannot start worker: MongoDB connection failed")
            sys.exit(1)
        db = client[DATABASE_NAME]
        repo = MongoArticleRepository(db)
        token_usage_repo = MongoTokenUsageRepository(db)
        vocab_repo = MongoVocabularyRepository(db)
        llm = LiteLLMAdapter()
        run_worker_loop(repo, token_usage_repo, vocab_repo, llm)
    except KeyboardInterrupt:
        logger.info("Worker stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
