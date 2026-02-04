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

from api.middleware.auth import get_current_user_required
from api.models import (
    SearchRequest,
    SearchResponse,
    User,
    VocabularyRequest,
    VocabularyResponse,
    VocabularyCount,
)
from services.dictionary_service import DictionaryService, LookupRequest
from utils.llm import get_llm_error_response
from utils.mongodb import (
    delete_vocabulary,
    get_vocabularies,
    get_vocabulary_by_id,
    get_vocabulary_counts,
    save_vocabulary,
    save_token_usage,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dictionary", tags=["dictionary"])


# Dependency injection for service
def get_dictionary_service() -> DictionaryService:
    """Create DictionaryService instance for dependency injection."""
    return DictionaryService()


@router.post("/search", response_model=SearchResponse)
async def search_word(
    request: SearchRequest,
    current_user: User = Depends(get_current_user_required),
    service: DictionaryService = Depends(get_dictionary_service)
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
            save_token_usage(
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
    current_user: User = Depends(get_current_user_required)
):
    """Add a word to vocabulary list.

    Args:
        request: Vocabulary request with word, lemma, definition, etc.
        current_user: Authenticated user

    Returns:
        VocabularyResponse with saved vocabulary data
    """
    vocabulary_id = save_vocabulary(
        article_id=request.article_id,
        word=request.word,
        lemma=request.lemma,
        definition=request.definition,
        sentence=request.sentence,
        language=request.language,
        related_words=request.related_words,
        span_id=request.span_id,
        user_id=current_user.id,
        metadata={
            'pos': request.pos,
            'gender': request.gender,
            'phonetics': request.phonetics,
            'conjugations': request.conjugations,
            'level': request.level,
            'examples': request.examples
        }
    )

    if not vocabulary_id:
        raise HTTPException(status_code=500, detail="Failed to save vocabulary")

    # Get the saved vocabulary to return
    vocabularies = get_vocabularies(article_id=request.article_id, user_id=current_user.id)
    vocabulary = next((v for v in vocabularies if v['id'] == vocabulary_id), None)

    if not vocabulary:
        raise HTTPException(status_code=500, detail="Vocabulary saved but not found")

    logger.info("Vocabulary added", extra={
        "vocabulary_id": vocabulary_id,
        "article_id": request.article_id,
        "lemma": request.lemma,
        "user_id": current_user.id
    })

    return VocabularyResponse(**vocabulary)


@router.get("/vocabularies", response_model=list[VocabularyCount])
async def get_vocabularies_list(
    language: str | None = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user_required)
):
    """Get aggregated vocabulary list grouped by lemma with counts.

    Args:
        language: Optional language filter
        skip: Number of entries to skip (for pagination)
        limit: Maximum number of entries to return (default: 100, max: 1000)
        current_user: Authenticated user

    Returns:
        List of vocabulary groups with counts (VocabularyCount)
    """
    # Enforce maximum limit
    limit = min(limit, 1000)

    word_counts = get_vocabulary_counts(
        language=language,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )

    logger.info("Grouped vocabularies retrieved", extra={
        "group_count": len(word_counts),
        "language": language,
        "skip": skip,
        "limit": limit,
        "user_id": current_user.id
    })

    return word_counts


@router.delete("/vocabularies/{vocabulary_id}")
async def delete_vocabulary_word(
    vocabulary_id: str,
    current_user: User = Depends(get_current_user_required)
):
    """Delete a vocabulary word.

    Args:
        vocabulary_id: Vocabulary ID to delete
        current_user: Authenticated user

    Returns:
        Success message
    """
    # Check if vocabulary exists and verify ownership
    vocabulary = get_vocabulary_by_id(vocabulary_id)
    if not vocabulary:
        raise HTTPException(status_code=404, detail="Vocabulary not found")

    # Verify ownership
    if vocabulary.get('user_id') != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this vocabulary"
        )

    success = delete_vocabulary(vocabulary_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete vocabulary")

    logger.info("Vocabulary deleted", extra={
        "vocabulary_id": vocabulary_id,
        "user_id": current_user.id
    })

    return {"message": "Vocabulary deleted successfully"}
