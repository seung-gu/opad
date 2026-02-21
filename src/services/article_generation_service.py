"""Article generation service — orchestrates article creation pipeline.

Submission: duplicate check → create → enqueue
Generation: vocabulary filtering → generation → save → token tracking
"""

import logging

from domain.model.article import Article, ArticleInputs, ArticleStatus
from domain.model.cefr import CEFRLevel
from domain.model.errors import DuplicateArticleError, EnqueueError, DomainError
from port.article_generator import ArticleGeneratorPort
from port.article_repository import ArticleRepository
from port.job_queue import JobQueuePort
from port.llm import LLMPort
from port.token_usage_repository import TokenUsageRepository
from port.vocabulary import VocabularyPort
from services.token_usage_service import track_agent_usage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Submission (API side): duplicate check → create → enqueue
# ---------------------------------------------------------------------------


def submit_generation(
    inputs: ArticleInputs,
    user_id: str,
    repo: ArticleRepository,
    job_queue: JobQueuePort,
    force: bool = False,
) -> Article:
    """Submit article generation request.

    Returns the created Article (with job_id set).
    Raises DuplicateArticleError or EnqueueError on failure.
    """
    logger.info("Article generation requested", extra={
        "userId": user_id,
        "topic": inputs.topic,
        "language": inputs.language
    })

    _check_duplicate(repo, job_queue, inputs, force, user_id)

    article = Article.create(inputs, user_id)

    if not repo.save(article):
        raise DomainError("Failed to save article to repository")
    
    logger.info("Article created", extra={"articleId": article.id, "jobId": article.job_id})

    _enqueue_job(job_queue, repo, article) 
    
    return article


def _check_duplicate(
    repo: ArticleRepository,
    job_queue: JobQueuePort,
    inputs: ArticleInputs,
    force: bool,
    user_id: str | None,
) -> None:
    """Raise DuplicateArticleError if a matching article exists."""
    if force:
        return

    existing = repo.find_duplicate(inputs, user_id, hours=24)
    if not existing:
        return

    job_data = None
    if existing.job_id:
        job_data = job_queue.get_status(existing.job_id)

    raise DuplicateArticleError(existing.id, job_data)


def _enqueue_job(
    job_queue: JobQueuePort,
    repo: ArticleRepository,
    article: Article,
) -> None:
    """Enqueue job or raise EnqueueError."""
    if not job_queue.update_status(
        article.job_id, 'queued', 0,
        'Job queued, waiting for worker...',
        article_id=article.id,
    ):
        raise EnqueueError("Failed to initialize job status")

    inputs = {
        'language': article.inputs.language,
        'level': article.inputs.level,
        'length': article.inputs.length,
        'topic': article.inputs.topic,
    }
    if not job_queue.enqueue(article.job_id, article.id, inputs, article.user_id):
        job_queue.update_status(
            article.job_id, 'failed', 0,
            'Failed to enqueue job', 'Queue service unavailable',
            article_id=article.id,
        )
        repo.update_status(article.id, ArticleStatus.FAILED)
        raise EnqueueError("Failed to enqueue job")


# ---------------------------------------------------------------------------
# Generation (Worker side): vocabulary → generate → save → track
# ---------------------------------------------------------------------------


def generate_article(
    article: Article,
    user_id: str | None,
    inputs: ArticleInputs,
    generator: ArticleGeneratorPort,
    repo: ArticleRepository,
    token_usage_repo: TokenUsageRepository | None = None,
    vocab: VocabularyPort | None = None,
    llm: LLMPort | None = None,
    job_id: str | None = None,
) -> bool:
    """Generate article content and save to repository.

    Returns:
        True if successful, False if generation or save failed.
    """
    # 1. Vocabulary filtering
    vocab_list = _get_vocabulary(user_id, inputs.language, inputs.level, vocab)

    # 2. Generate via port
    result = generator.generate(inputs, vocab_list, job_id=job_id or "", article_id=article.id)

    # 4. Update article domain object
    article.complete(
        content=result.content,
        source=result.source,
        edit_history=result.edit_history,
    )

    # 5. Save to repository
    if not repo.save(article):
        logger.error("Failed to save article", extra={"articleId": article.id})
        return False

    # 6. Track token usage
    if user_id and token_usage_repo and result.agent_usage:
        track_agent_usage(
            token_usage_repo,
            result.agent_usage,
            user_id,
            article.id,
            job_id or "",
            llm=llm,
        )

    return True


def _get_vocabulary(
    user_id: str | None,
    language: str,
    level: str,
    vocab: VocabularyPort | None,
) -> list[str]:
    """Fetch user's vocabulary filtered by target level."""
    if not user_id or not language or not vocab:
        return []

    levels = CEFRLevel.range(level, max_above=1)
    vocab_list = vocab.find_lemmas(
        user_id=user_id,
        language=language,
        levels=levels,
        limit=50,
    )
    return vocab_list if vocab_list else []
