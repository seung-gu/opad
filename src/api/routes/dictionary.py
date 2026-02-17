"""Dictionary API routes for word definitions.

This module handles HTTP concerns for dictionary endpoints.
Business logic is delegated to dictionary_service module functions.

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
from services import dictionary_service, vocabulary_service
from api.dependencies import get_dictionary_port, get_llm_port, get_token_usage_repo, get_vocab_repo
from port.dictionary import DictionaryPort
from port.llm import LLMPort, LLMTimeoutError, LLMRateLimitError, LLMAuthError, LLMError
from port.token_usage_repository import TokenUsageRepository as TokenUsageRepo
from port.vocabulary_repository import VocabularyRepository
from domain.model.vocabulary import GrammaticalInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dictionary", tags=["dictionary"])


@router.post("/search", response_model=SearchResponse)
async def search_word(
    request: SearchRequest,
    current_user: UserResponse = Depends(get_current_user_required),
    dictionary: DictionaryPort = Depends(get_dictionary_port),
    llm: LLMPort = Depends(get_llm_port),
    token_usage_repo: TokenUsageRepo = Depends(get_token_usage_repo),
):
    """Search for word definition and lemma using hybrid approach.

    This endpoint uses a hybrid approach combining:
    1. LLM (reduced prompt): Extracts lemma, related_words, and CEFR level
    2. Free Dictionary API: Provides definition, POS, pronunciation, and forms

    If the hybrid approach fails, falls back to full LLM.

    Requires authentication to prevent API abuse.
    """
    try:
        result = await dictionary_service.lookup(
            word=request.word,
            sentence=request.sentence,
            language=request.language,
            dictionary=dictionary,
            llm=llm,
            token_usage_repo=token_usage_repo,
            user_id=current_user.id,
            article_id=request.article_id,
        )

        return SearchResponse(
            lemma=result["lemma"],
            definition=result["definition"],
            related_words=result.get("related_words"),
            pos=result.get("pos"),
            gender=result.get("gender"),
            phonetics=result.get("phonetics"),
            conjugations=result.get("conjugations"),
            level=result.get("level"),
            examples=result.get("examples"),
        )

    except HTTPException:
        raise
    except LLMTimeoutError as e:
        logger.error("LLM timeout", extra={"word": request.word, "error": str(e)})
        raise HTTPException(status_code=504, detail="LLM provider timeout")
    except LLMRateLimitError as e:
        logger.error("LLM rate limit", extra={"word": request.word, "error": str(e)})
        raise HTTPException(status_code=429, detail="LLM provider rate limit exceeded")
    except LLMAuthError as e:
        logger.error("LLM auth error", extra={"word": request.word, "error": str(e)})
        raise HTTPException(status_code=401, detail="LLM provider authentication failed")
    except LLMError as e:
        logger.error("LLM error", extra={"word": request.word, "error": str(e)})
        raise HTTPException(status_code=502, detail="LLM provider error")
    except Exception as e:
        logger.error("Unexpected error in dictionary search",
                     extra={"error": str(e), "word": request.word}, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/vocabulary", response_model=VocabularyResponse)
async def add_vocabulary(
    request: VocabularyRequest,
    current_user: UserResponse = Depends(get_current_user_required),
    repo: VocabularyRepository = Depends(get_vocab_repo),
):
    """Add a word to vocabulary list."""
    vocab = vocabulary_service.save(
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

    if not vocab:
        raise HTTPException(status_code=500, detail="Failed to save vocabulary")

    logger.info("Vocabulary added", extra={
        "vocabulary_id": vocab.id,
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

    domain_counts = repo.count_by_lemma(
        language=language, user_id=current_user.id, skip=skip, limit=limit,
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
