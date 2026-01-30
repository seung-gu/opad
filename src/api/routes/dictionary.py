"""Dictionary API routes for word definitions.

This module handles word definition requests using OpenAI API:
- POST /dictionary/search: Search for word definition and lemma from sentence context
- POST /dictionary/vocabulary: Add a word to vocabulary list
- GET /dictionary/vocabularies: Get aggregated vocabulary list
- DELETE /dictionary/vocabularies/{id}: Delete a vocabulary word
"""

import logging
from fastapi import APIRouter, Depends, HTTPException

from api.middleware.auth import get_current_user_required
from api.models import SearchRequest, SearchResponse, User, VocabularyRequest, VocabularyResponse, VocabularyCount
from utils.llm import call_llm_with_tracking, parse_json_from_content, get_llm_error_response
from utils.prompts import build_word_definition_prompt
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


@router.post("/search", response_model=SearchResponse)
async def search_word(
    request: SearchRequest,
    current_user: User = Depends(get_current_user_required)
):
    """Search for word definition and lemma using OpenAI API.

    Requires authentication to prevent API abuse.

    Args:
        request: Search request with word, sentence, and language
        current_user: Authenticated user (required)

    Returns:
        SearchResponse with lemma, definition, and grammatical metadata
    """
    prompt = build_word_definition_prompt(
        language=request.language,
        sentence=request.sentence,
        word=request.word
    )
    
    try:
        content, stats = await call_llm_with_tracking(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4.1-mini",
            max_tokens=200,
            temperature=0
        )

        # Save token usage to database
        save_token_usage(
            user_id=current_user.id,
            operation="dictionary_search",
            model=stats.model,
            prompt_tokens=stats.prompt_tokens,
            completion_tokens=stats.completion_tokens,
            estimated_cost=stats.estimated_cost,
            metadata={"word": request.word, "language": request.language}
        )

        # Parse JSON response
        result = parse_json_from_content(content)
        
        if result:
            lemma = result.get("lemma", request.word)
            definition = result.get("definition", "Definition not found")
            related_words = result.get("related_words", None)
            pos = result.get("pos", None)
            gender = result.get("gender", None)
            conjugations = result.get("conjugations", None)
            level = result.get("level", None)

            logger.info("Word definition extracted", extra={
                "word": request.word,
                "lemma": lemma,
                "related_words": related_words,
                "pos": pos,
                "gender": gender,
                "level": level,
                "language": request.language
            })

            return SearchResponse(
                lemma=lemma,
                definition=definition,
                related_words=related_words,
                pos=pos,
                gender=gender,
                conjugations=conjugations,
                level=level
            )
        else:
            # Fallback: return content as definition if JSON parsing fails
            logger.warning("Failed to parse JSON, using content as definition", extra={
                "word": request.word,
                "content_preview": content[:200]
            })
            return SearchResponse(
                lemma=request.word,
                definition=content if len(content) < 500 else "Definition not found"
            )
    
    except Exception as e:
        status_code, detail = get_llm_error_response(e)
        logger.error("LLM error", extra={"error": str(e)}, exc_info=True)
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
        pos=request.pos,
        gender=request.gender,
        conjugations=request.conjugations,
        level=request.level
    )

    if not vocabulary_id:
        raise HTTPException(status_code=500, detail="Failed to save vocabulary")

    # Get the saved vocabulary to return
    vocabularies = get_vocabularies(article_id=request.article_id, user_id=current_user.id)
    vocabulary = next((v for v in vocabularies if v['id'] == vocabulary_id), None)

    if not vocabulary:
        raise HTTPException(status_code=500, detail="Vocabulary saved but not found")

    logger.info("Vocabulary added", extra={
        "vocabularyId": vocabulary_id,
        "articleId": request.article_id,
        "lemma": request.lemma,
        "userId": current_user.id
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
        "groupCount": len(word_counts),
        "language": language,
        "skip": skip,
        "limit": limit,
        "userId": current_user.id
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
        raise HTTPException(status_code=403, detail="You don't have permission to delete this vocabulary")

    success = delete_vocabulary(vocabulary_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete vocabulary")

    logger.info("Vocabulary deleted", extra={
        "vocabularyId": vocabulary_id,
        "userId": current_user.id
    })

    return {"message": "Vocabulary deleted successfully"}
