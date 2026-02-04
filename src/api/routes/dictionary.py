"""Dictionary API routes for word definitions.

This module handles word definition requests using a hybrid approach:
- LLM for lemma extraction and CEFR level classification
- Free Dictionary API for pronunciation, definitions, and grammatical forms
- Fallback to full LLM when API is unavailable

Endpoints:
- POST /dictionary/search: Search for word definition and lemma from sentence context
- POST /dictionary/vocabulary: Add a word to vocabulary list
- GET /dictionary/vocabularies: Get aggregated vocabulary list
- DELETE /dictionary/vocabularies/{id}: Delete a vocabulary word
"""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.middleware.auth import get_current_user_required
from api.models import SearchRequest, SearchResponse, User, VocabularyRequest, VocabularyResponse, VocabularyCount
from utils.dictionary_api import fetch_from_free_dictionary_api, DictionaryAPIResult
from utils.llm import call_llm_with_tracking, parse_json_from_content, get_llm_error_response
from utils.prompts import build_word_definition_prompt, build_reduced_word_definition_prompt
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

# Token limits for LLM calls
REDUCED_PROMPT_MAX_TOKENS = 500
FULL_PROMPT_MAX_TOKENS = 2000


async def _call_llm_reduced(
    request: SearchRequest
) -> tuple[dict[str, Any] | None, Any]:
    """Call LLM with reduced prompt for lemma and level only.

    Args:
        request: Search request with word, sentence, and language.

    Returns:
        Tuple of (parsed result dict, token stats) or (None, None) on error.
    """
    prompt = build_reduced_word_definition_prompt(
        language=request.language,
        sentence=request.sentence,
        word=request.word
    )

    content, stats = await call_llm_with_tracking(
        messages=[{"role": "user", "content": prompt}],
        model="openai/gpt-4.1",
        max_tokens=REDUCED_PROMPT_MAX_TOKENS,
        temperature=0
    )

    result = parse_json_from_content(content)
    return result, stats


def _merge_llm_and_api_results(
    llm_data: dict[str, Any],
    dict_data: DictionaryAPIResult,
    word: str
) -> tuple[str, str | None, str | None, str | None, str | None, str | None, str | None, dict[str, str] | None, list[str] | None]:
    """Merge LLM and Dictionary API results.

    Args:
        llm_data: Parsed LLM response with lemma, related_words, level.
        dict_data: Dictionary API result with definition, pos, gender, phonetics, forms, examples.
        word: Original word for fallback lemma.

    Returns:
        Tuple of (lemma, related_words, level, definition, pos, gender, phonetics, conjugations, examples).
    """
    # Extract LLM fields
    lemma = llm_data.get("lemma", word)
    related_words = llm_data.get("related_words")
    level = llm_data.get("level")

    # Extract Dictionary API fields
    definition = dict_data.definition
    pos = dict_data.pos
    gender = dict_data.gender
    phonetics = dict_data.phonetics
    examples = dict_data.examples

    # Convert forms to conjugations format if available
    # Supports both verb forms (present, past, participle, auxiliary)
    # and noun forms (genitive, plural, feminine)
    conjugations: dict[str, str] | None = None
    if dict_data.forms:
        conjugations = {}

        # Verb forms
        if dict_data.forms.get("present"):
            conjugations["present"] = dict_data.forms["present"]
        if dict_data.forms.get("past"):
            conjugations["past"] = dict_data.forms["past"]
        if dict_data.forms.get("participle"):
            conjugations["participle"] = dict_data.forms["participle"]
        if dict_data.forms.get("auxiliary"):
            conjugations["auxiliary"] = dict_data.forms["auxiliary"]

        # Noun forms
        if dict_data.forms.get("genitive"):
            conjugations["genitive"] = dict_data.forms["genitive"]
        if dict_data.forms.get("plural"):
            conjugations["plural"] = dict_data.forms["plural"]

        conjugations = conjugations or None

    return lemma, related_words, level, definition, pos, gender, phonetics, conjugations, examples


def _build_hybrid_response(
    lemma: str,
    definition: str,
    related_words: str | None,
    pos: str | None,
    gender: str | None,
    phonetics: str | None,
    conjugations: dict[str, str] | None,
    level: str | None,
    examples: list[str] | None = None
) -> SearchResponse:
    """Build SearchResponse from hybrid lookup results.

    Args:
        lemma: Word lemma/base form.
        definition: Word definition.
        related_words: Related words or phrases.
        pos: Part of speech.
        gender: Grammatical gender.
        phonetics: IPA pronunciation.
        conjugations: Verb conjugations or noun forms.
        level: CEFR level.
        examples: Example sentences from dictionary.

    Returns:
        SearchResponse with all fields.
    """
    return SearchResponse(
        lemma=lemma,
        definition=definition,
        related_words=related_words,
        pos=pos,
        gender=gender,
        phonetics=phonetics,
        conjugations=conjugations,
        level=level,
        examples=examples
    )


async def _fallback_full_llm_search(
    request: SearchRequest,
    current_user: User
) -> SearchResponse:
    """Fallback to full LLM search when hybrid approach fails.

    This uses the original full prompt that requests all fields
    from the LLM (lemma, definition, pos, gender, conjugations, level).

    Args:
        request: Search request with word, sentence, and language.
        current_user: Authenticated user.

    Returns:
        SearchResponse with all fields from LLM.

    Raises:
        HTTPException: On LLM errors.
    """
    prompt = build_word_definition_prompt(
        language=request.language,
        sentence=request.sentence,
        word=request.word
    )

    try:
        content, stats = await call_llm_with_tracking(
            messages=[{"role": "user", "content": prompt}],
            model="openai/gpt-4.1-mini",
            max_tokens=FULL_PROMPT_MAX_TOKENS,
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
            article_id=request.article_id,
            metadata={
                "word": request.word,
                "language": request.language,
                "source": "llm"
            }
        )

        result = parse_json_from_content(content)

        if result:
            lemma = result.get("lemma", request.word)
            definition = result.get("definition", "Definition not found")
            related_words = result.get("related_words")
            pos = result.get("pos")
            gender = result.get("gender")
            conjugations = result.get("conjugations")
            level = result.get("level")

            logger.info("Word definition extracted (full LLM fallback)", extra={
                "word": request.word,
                "lemma": lemma,
                "related_words": related_words,
                "pos": pos,
                "gender": gender,
                "level": level,
                "language": request.language,
                "source": "llm"
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
            logger.warning("Failed to parse JSON in fallback, using content", extra={
                "word": request.word,
                "content_preview": content[:200]
            })
            return SearchResponse(
                lemma=request.word,
                definition=content if len(content) < 500 else "Definition not found"
            )

    except Exception as e:
        status_code, detail = get_llm_error_response(e)
        logger.error("LLM error in fallback", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=status_code, detail=detail)


@router.post("/search", response_model=SearchResponse)
async def search_word(
    request: SearchRequest,
    current_user: User = Depends(get_current_user_required)
):
    """Search for word definition and lemma using hybrid approach.

    This endpoint uses a hybrid approach combining:
    1. LLM (reduced prompt): Extracts lemma, related_words, and CEFR level
    2. Free Dictionary API: Provides definition, POS, pronunciation, and forms

    If the Free Dictionary API fails, falls back to full LLM approach.

    Requires authentication to prevent API abuse.

    Args:
        request: Search request with word, sentence, and language
        current_user: Authenticated user (required)

    Returns:
        SearchResponse with lemma, definition, and grammatical metadata
    """
    try:
        # Step 1: Call LLM first to get lemma (needed for API lookup)
        llm_result = await _call_llm_reduced(request)

        # Handle LLM result
        llm_data: dict[str, Any] | None = None
        stats = None

        if isinstance(llm_result, Exception):
            logger.warning(
                "LLM call failed in hybrid search",
                extra={"error": str(llm_result), "word": request.word}
            )
            # Fall back to full LLM search
            return await _fallback_full_llm_search(request, current_user)
        else:
            llm_data, stats = llm_result

        if llm_data is None:
            logger.warning(
                "LLM returned unparseable result, falling back to full LLM",
                extra={"word": request.word}
            )
            return await _fallback_full_llm_search(request, current_user)

        # Step 2: Call Dictionary API with lemma from LLM
        lemma = llm_data.get("lemma", request.word)
        dict_api_result = await fetch_from_free_dictionary_api(
            word=lemma,
            language=request.language
        )

        # Handle Dictionary API result
        dict_data: DictionaryAPIResult | None = dict_api_result
        source = "hybrid" if dict_data else "llm"

        # If no dictionary data or no definition, fall back to full LLM
        if dict_data is None or dict_data.definition is None:
            logger.info(
                "Dictionary API missing definition, falling back to full LLM",
                extra={"word": request.word, "lemma": lemma}
            )
            return await _fallback_full_llm_search(request, current_user)

        # Merge LLM and Dictionary API results
        (
            lemma, related_words, level,
            definition, pos, gender, phonetics, conjugations, examples
        ) = _merge_llm_and_api_results(llm_data, dict_data, request.word)

        # Only include phonetics for English (IPA from Free Dictionary API is most accurate for English)
        if request.language != "English":
            phonetics = None

        # Save token usage to database
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
                    "source": source,
                    "phonetics": phonetics
                }
            )

        logger.info("Word definition extracted (hybrid)", extra={
            "word": request.word,
            "lemma": lemma,
            "related_words": related_words,
            "pos": pos,
            "gender": gender,
            "level": level,
            "language": request.language,
            "source": source,
            "phonetics": phonetics
        })

        return _build_hybrid_response(
            lemma=lemma,
            definition=definition,
            related_words=related_words,
            pos=pos,
            gender=gender,
            phonetics=phonetics,
            conjugations=conjugations,
            level=level,
            examples=examples
        )

    except HTTPException:
        # Re-raise HTTP exceptions from fallback
        raise
    except Exception as e:
        logger.error(
            "Unexpected error in hybrid search, falling back to full LLM",
            extra={"error": str(e), "word": request.word},
            exc_info=True
        )
        return await _fallback_full_llm_search(request, current_user)


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
