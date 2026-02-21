"""Article-related API routes."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from api.models import ArticleResponse, GenerateRequest, GenerateResponse, JobResponse, ArticleListResponse, UserResponse, VocabularyResponse
from api.security import get_current_user_required
from api.dependencies import get_article_repo, get_job_queue, get_vocab_repo
from port.article_repository import ArticleRepository
from port.job_queue import JobQueuePort
from domain.model.article import ArticleInputs, ArticleStatus, Article
from domain.model.errors import DomainError, DuplicateArticleError, EnqueueError
from port.vocabulary_repository import VocabularyRepository
from services.article_generation_service import submit_generation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/articles", tags=["articles"])


def _build_article_response(article: Article) -> dict:
    """Build article response dict from Article domain model."""
    created_at = article.created_at

    # Format timestamp
    if created_at.tzinfo is not None:
        formatted_time = created_at.isoformat()
    else:
        formatted_time = created_at.isoformat() + 'Z'

    return {
        'id': article.id,
        'language': article.inputs.language,
        'level': article.inputs.level,
        'length': article.inputs.length,
        'topic': article.inputs.topic,
        'status': article.status.value if isinstance(article.status, ArticleStatus) else article.status,
        'created_at': formatted_time,
        'user_id': article.user_id,
        'job_id': article.job_id,
        'inputs': {
            'language': article.inputs.language,
            'level': article.inputs.level,
            'length': article.inputs.length,
            'topic': article.inputs.topic,
        }
    }


def _check_ownership(article: Article, current_user: UserResponse, article_id: str, action: str = "access") -> None:
    """Check if the current user owns the article."""
    if not article.is_owned_by(current_user.id):
        logger.warning(
            f"Unauthorized {action} attempt",
            extra={
                "articleId": article_id,
                "articleUserId": article.user_id,
                "requestUserId": current_user.id
            }
        )
        raise HTTPException(
            status_code=403,
            detail=f"You don't have permission to {action} this article"
        )


def _get_article_or_404(
    repo: ArticleRepository, article_id: str, check_deleted: bool = True
) -> Article:
    """Retrieve article or raise 404."""
    article = repo.get_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if check_deleted and article.is_deleted:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.get("")
async def list_articles(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    language: Optional[str] = None,
    level: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user_required),
    repo: ArticleRepository = Depends(get_article_repo),
):
    """Get article list with filters and pagination."""
    if limit > 100:
        limit = 100
    if limit < 1:
        limit = 1

    try:
        status_enum = ArticleStatus(status) if status else None
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid status: {status}")

    result = repo.find_many(
        skip, limit, status_enum, language, level, current_user.id, exclude_deleted=True,
    )

    article_responses = []
    for article in result.items:
        try:
            article_responses.append(_build_article_response(article))
        except Exception as e:
            logger.warning("Skipping invalid article", extra={
                "articleId": article.id,
                "error": str(e)
            })

    logger.info("Listed articles", extra={
        "count": len(article_responses),
        "total": result.total,
        "skip": skip,
        "limit": limit
    })

    return ArticleListResponse(
        articles=article_responses,
        total=result.total,
        skip=skip,
        limit=limit
    )


@router.post("/generate", response_model=GenerateResponse)
async def generate_article(
    request: GenerateRequest,
    force: bool = False,
    current_user: UserResponse = Depends(get_current_user_required),
    repo: ArticleRepository = Depends(get_article_repo),
    job_queue: JobQueuePort = Depends(get_job_queue),
):
    """Create article and start generation (unified endpoint)."""
    inputs = ArticleInputs(
        language=request.language,
        level=request.level,
        length=request.length,
        topic=request.topic,
    )

    try:
        article = submit_generation(inputs, current_user.id, repo, job_queue, force)
    except DuplicateArticleError as e:
        existing_job = None
        if e.job_data:
            try:
                existing_job = JobResponse(**e.job_data)
            except Exception:
                pass
        raise HTTPException(status_code=409, detail={
            "error": "Duplicate article detected",
            "message": "An article with identical parameters was created within the last 24 hours.",
            "existing_job": existing_job.model_dump(mode='json') if existing_job else None,
            "article_id": e.article_id,
        })
    except EnqueueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except DomainError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return GenerateResponse(
        job_id=article.job_id,
        article_id=article.id,
        message="Article generation started. Use job_id to track progress.",
    )


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: str,
    current_user: UserResponse = Depends(get_current_user_required),
    repo: ArticleRepository = Depends(get_article_repo),
):
    """Get article metadata by ID."""
    article = _get_article_or_404(repo, article_id)
    _check_ownership(article, current_user, article_id)

    response_data = _build_article_response(article)
    return ArticleResponse(**response_data)


@router.get("/{article_id}/content")
async def get_article_content(
    article_id: str,
    current_user: UserResponse = Depends(get_current_user_required),
    repo: ArticleRepository = Depends(get_article_repo),
):
    """Get article content (markdown)."""
    from fastapi.responses import Response

    article = _get_article_or_404(repo, article_id)
    _check_ownership(article, current_user, article_id, "access")

    if not article.has_content:
        raise HTTPException(status_code=404, detail="Article content not found")

    return Response(content=article.content, media_type='text/markdown')


@router.get("/{article_id}/vocabularies", response_model=list[VocabularyResponse])
async def get_article_vocabularies(
    article_id: str,
    current_user: UserResponse = Depends(get_current_user_required),
    repo: ArticleRepository = Depends(get_article_repo),
    vocab_repo: VocabularyRepository = Depends(get_vocab_repo),
):
    """Get vocabularies for a specific article."""
    article = _get_article_or_404(repo, article_id)
    _check_ownership(article, current_user, article_id, "access")

    vocabs = vocab_repo.find(article_id=article_id, user_id=current_user.id)

    logger.info("Article vocabularies retrieved", extra={
        "articleId": article_id,
        "count": len(vocabs),
        "userId": current_user.id
    })

    return [
        {
            'id': v.id,
            'article_id': v.article_id,
            'word': v.word,
            'lemma': v.lemma,
            'definition': v.definition,
            'sentence': v.sentence,
            'language': v.language,
            'related_words': v.related_words,
            'span_id': v.span_id,
            'created_at': v.created_at,
            'user_id': v.user_id,
            'pos': v.grammar.pos if v.grammar else None,
            'gender': v.grammar.gender if v.grammar else None,
            'phonetics': v.grammar.phonetics if v.grammar else None,
            'conjugations': v.grammar.conjugations if v.grammar else None,
            'level': v.level,
            'examples': v.grammar.examples if v.grammar else None,
        }
        for v in vocabs
    ]


@router.delete("/{article_id}")
async def delete_article(
    article_id: str,
    current_user: UserResponse = Depends(get_current_user_required),
    repo: ArticleRepository = Depends(get_article_repo),
):
    """Soft delete article."""
    article = _get_article_or_404(repo, article_id, check_deleted=False)
    _check_ownership(article, current_user, article_id, "delete")

    success = repo.delete(article_id)
    if not success:
        raise HTTPException(status_code=503, detail="Failed to delete article")

    logger.info("Article deleted via API", extra={"articleId": article_id, "userId": current_user.id})

    return {
        "success": True,
        "article_id": article_id,
        "message": "Article soft deleted (status='deleted')"
    }
