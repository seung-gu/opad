"""Dictionary API routes for word definitions.

This module handles HTTP concerns for dictionary endpoints.
Business logic is delegated to DictionaryService.

Endpoints:
- POST /dictionary/search: Search for word definition and lemma from sentence context
- POST /dictionary/vocabulary: Add a word to vocabulary list
- GET /dictionary/vocabularies: Get aggregated vocabulary list
- DELETE /dictionary/vocabularies/{id}: Delete a vocabulary word
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from api.security import get_current_user_required
from api.models import (
    SearchRequest,
    SearchResponse,
    UserResponse,
    VocabularyRequest,
    VocabularyResponse,
    VocabularyCount,
)
from services.dictionary_service import DictionaryService, LookupRequest
from services import vocabulary_service
from utils.llm import get_llm_error_response
from api.dependencies import get_token_usage_repo, get_vocab_repo
from port.token_usage_repository import TokenUsageRepository
from port.vocabulary_repository import VocabularyRepository
from domain.model.vocabulary import GrammaticalInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dictionary", tags=["dictionary"])


# Dependency injection for service
def get_dictionary_service() -> DictionaryService:
    """Create DictionaryService instance for dependency injection."""
    return DictionaryService()


@router.post("/search", response_model=SearchResponse)
async def search_word(
    request: SearchRequest,
    current_user: UserResponse = Depends(get_current_user_required),
    service: DictionaryService = Depends(get_dictionary_service),
    token_usage_repo: TokenUsageRepository = Depends(get_token_usage_repo),
):
    """Search for word definition and lemma using hybrid approach.

    This endpoint uses a hybrid approach combining:
    1. LLM (reduced prompt): Extracts lemma, related_words, and CEFR level
    2. Free Dictionary API: Provides definition, POS, pronunciation, and forms

    If the hybrid approach fails, falls back to full LLM.

    Requires authentication to prevent API abuse.
    """
    try:
        # Convert API request to service request
        lookup_request = LookupRequest(
            word=request.word,
            sentence=request.sentence,
            language=request.language,
            article_id=request.article_id
        )

        # Perform lookup via service
        result = await service.lookup(lookup_request)

        # Track token usage
        stats = service.last_token_stats
        if stats:
            token_usage_repo.save(
                user_id=current_user.id,
                operation="dictionary_search",
                model=stats.model,
                prompt_tokens=stats.prompt_tokens,
                completion_tokens=stats.completion_tokens,
                estimated_cost=stats.estimated_cost,
                article_id=request.article_id,
                metadata={
                    "word": request.word,
                    "language": request.language,
                    "source": result.source,
                    "phonetics": result.phonetics
                }
            )

        # Convert service result to API response
        return SearchResponse(
            lemma=result.lemma,
            definition=result.definition,
            related_words=result.related_words,
            pos=result.pos,
            gender=result.gender,
            phonetics=result.phonetics,
            conjugations=result.conjugations,
            level=result.level,
            examples=result.examples
        )

    except HTTPException:
        raise
    except Exception as e:
        status_code, detail = get_llm_error_response(e)
        logger.error(
            "Error in dictionary search",
            extra={"error": str(e), "word": request.word},
            exc_info=True
        )
        raise HTTPException(status_code=status_code, detail=detail)


@router.post("/vocabulary", response_model=VocabularyResponse)
async def add_vocabulary(
    request: VocabularyRequest,
    current_user: UserResponse = Depends(get_current_user_required),
    repo: VocabularyRepository = Depends(get_vocab_repo),
):
    """Add a word to vocabulary list."""
    vocabulary_id = vocabulary_service.save_vocabulary(
        repo,
        article_id=request.article_id,
        word=request.word,
        lemma=request.lemma,
        definition=request.definition,
        sentence=request.sentence,
        language=request.language,
        related_words=request.related_words,
        span_id=request.span_id,
        user_id=current_user.id,
        grammar=GrammaticalInfo(
            pos=request.pos,
            gender=request.gender,
            phonetics=request.phonetics,
            conjugations=request.conjugations,
            level=request.level,
            examples=request.examples,
        ),
    )

    if not vocabulary_id:
        raise HTTPException(status_code=500, detail="Failed to save vocabulary")

    vocab = repo.get_by_id(vocabulary_id)
    if not vocab:
        raise HTTPException(status_code=500, detail="Vocabulary saved but not found")

    logger.info("Vocabulary added", extra={
        "vocabulary_id": vocabulary_id,
        "article_id": request.article_id,
        "lemma": request.lemma,
        "user_id": current_user.id
    })

    return VocabularyResponse(
        id=vocab.id,
        article_id=vocab.article_id,
        word=vocab.word,
        lemma=vocab.lemma,
        definition=vocab.definition,
        sentence=vocab.sentence,
        language=vocab.language,
        created_at=vocab.created_at,
        related_words=vocab.related_words,
        span_id=vocab.span_id,
        user_id=vocab.user_id,
        pos=vocab.grammar.pos if vocab.grammar else None,
        gender=vocab.grammar.gender if vocab.grammar else None,
        phonetics=vocab.grammar.phonetics if vocab.grammar else None,
        conjugations=vocab.grammar.conjugations if vocab.grammar else None,
        level=vocab.grammar.level if vocab.grammar else None,
        examples=vocab.grammar.examples if vocab.grammar else None,
    )


@router.get("/vocabularies", response_model=list[VocabularyCount])
async def get_vocabularies_list(
    language: str | None = None,
    skip: int = 0,
    limit: int = 100,
    current_user: UserResponse = Depends(get_current_user_required),
    repo: VocabularyRepository = Depends(get_vocab_repo),
):
    """Get aggregated vocabulary list grouped by lemma with counts."""
    limit = min(limit, 1000)

    domain_counts = vocabulary_service.get_counts(
        repo, language=language, user_id=current_user.id, skip=skip, limit=limit,
    )

    result = []
    for dc in domain_counts:
        v = dc.vocabulary
        g = v.grammar
        result.append(VocabularyCount(
            id=v.id,
            article_id=v.article_id,
            word=v.word,
            lemma=v.lemma,
            definition=v.definition,
            sentence=v.sentence,
            language=v.language,
            related_words=v.related_words,
            span_id=v.span_id,
            created_at=v.created_at,
            user_id=v.user_id,
            count=dc.count,
            article_ids=dc.article_ids,
            pos=g.pos if g else None,
            gender=g.gender if g else None,
            phonetics=g.phonetics if g else None,
            conjugations=g.conjugations if g else None,
            level=g.level if g else None,
            examples=g.examples if g else None,
        ))

    logger.info("Grouped vocabularies retrieved", extra={
        "group_count": len(result),
        "language": language,
        "user_id": current_user.id
    })

    return result


@router.delete("/vocabularies/{vocabulary_id}")
async def delete_vocabulary_word(
    vocabulary_id: str,
    current_user: UserResponse = Depends(get_current_user_required),
    repo: VocabularyRepository = Depends(get_vocab_repo),
):
    """Delete a vocabulary word."""
    vocab = repo.get_by_id(vocabulary_id)
    if not vocab:
        raise HTTPException(status_code=404, detail="Vocabulary not found")

    if vocab.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this vocabulary"
        )

    success = repo.delete(vocabulary_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete vocabulary")

    logger.info("Vocabulary deleted", extra={
        "vocabulary_id": vocabulary_id,
        "user_id": current_user.id
    })

    return {"message": "Vocabulary deleted successfully"}
