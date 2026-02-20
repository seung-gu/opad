"""Dictionary API routes for word definitions.

This module handles HTTP concerns for dictionary search.
Business logic is delegated to dictionary_service module functions.

Endpoints:
- POST /dictionary/search: Search for word definition and lemma from sentence context
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from api.security import get_current_user_required
from api.models import (
    SearchRequest,
    SearchResponse,
    UserResponse,
)
from services import dictionary_service
from api.dependencies import get_dictionary_port, get_llm_port, get_nlp_port, get_token_usage_repo
from port.dictionary import DictionaryPort
from port.llm import LLMPort, LLMTimeoutError, LLMRateLimitError, LLMAuthError, LLMError
from port.nlp import NLPPort
from port.token_usage_repository import TokenUsageRepository as TokenUsageRepo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dictionary", tags=["dictionary"])


@router.post("/search", response_model=SearchResponse)
async def search_word(
    request: SearchRequest,
    current_user: UserResponse = Depends(get_current_user_required),
    dictionary: DictionaryPort = Depends(get_dictionary_port),
    llm: LLMPort = Depends(get_llm_port),
    nlp: NLPPort = Depends(get_nlp_port),
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
            nlp=nlp,
            token_usage_repo=token_usage_repo,
            user_id=current_user.id,
            article_id=request.article_id,
        )

        return SearchResponse(
            lemma=result.lemma,
            definition=result.definition,
            related_words=result.related_words,
            pos=result.grammar.pos,
            gender=result.grammar.gender,
            phonetics=result.grammar.phonetics,
            conjugations=result.grammar.conjugations,
            level=result.level,
            examples=result.grammar.examples,
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
