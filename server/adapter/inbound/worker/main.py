"""Worker service entry point."""

import logging
import sys
from functools import partial
from pathlib import Path

# Add server to path (main.py is at server/adapter/inbound/worker/main.py)
sys.path.insert(0, str(Path(__file__).parents[3]))

from adapter.inbound.worker.processor import run_worker_loop
from adapter.outbound.crew.article_generator import CrewAIArticleGenerator
from adapter.outbound.mongodb.article_repository import MongoArticleRepository
from adapter.outbound.mongodb.connection import DATABASE_NAME, get_mongodb_client
from adapter.outbound.mongodb.token_usage_repository import MongoTokenUsageRepository
from adapter.outbound.mongodb.vocabulary_repository import MongoVocabularyRepository
from adapter.outbound.redis_job_queue import RedisJobQueueAdapter
from services.article_generation_service import generate_article
from utils.logging import setup_structured_logging

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

        # Job queue and article generator via ports
        job_queue = RedisJobQueueAdapter()
        if not job_queue.ping():
            logger.error("Cannot start worker: Redis connection failed")
            sys.exit(1)

        generator = CrewAIArticleGenerator(job_queue)
        generate = partial(
            generate_article,
            generator=generator,
            repo=repo,
            token_usage_repo=token_usage_repo,
            vocab=vocab_repo,
        )

        run_worker_loop(repo, job_queue, generate)
    except KeyboardInterrupt:
        logger.info("Worker stopped")
    except Exception:
        logger.exception("Fatal error")
        sys.exit(1)


if __name__ == "__main__":
    main()
