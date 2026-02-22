"""Article generation service — orchestrates article content generation.

Worker-side flow: vocabulary filtering → generation → save → token tracking
"""

import logging

from domain.model.article import Article, ArticleInputs
from domain.model.cefr import CEFRLevel
from port.article_generator import ArticleGeneratorPort
from port.article_repository import ArticleRepository
from port.llm import LLMPort
from port.token_usage_repository import TokenUsageRepository
from port.vocabulary_repository import VocabularyRepository
from services.token_usage_service import track_agent_usage

logger = logging.getLogger(__name__)


def generate_article(
    article: Article,
    user_id: str | None,
    inputs: ArticleInputs,
    generator: ArticleGeneratorPort,
    repo: ArticleRepository,
    token_usage_repo: TokenUsageRepository | None = None,
    vocab: VocabularyRepository | None = None,
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

    # 3. Update article domain object
    article.complete(
        content=result.content,
        source=result.source,
        edit_history=result.edit_history,
    )

    # 4. Save to repository
    if not repo.save(article):
        logger.error("Failed to save article", extra={"articleId": article.id})
        return False

    # 5. Track token usage
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
    vocab: VocabularyRepository | None,
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
