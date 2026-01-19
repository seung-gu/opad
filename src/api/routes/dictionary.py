"""Dictionary API routes for word definitions.

This module handles word definition requests using OpenAI API:
- POST /dictionary/define: Get word definition and lemma from sentence context
"""

import logging
from fastapi import APIRouter, HTTPException

from api.models import DefineRequest, DefineResponse
from utils.llm import call_openai_chat, parse_json_from_content, get_llm_error_response
from utils.prompts import build_word_definition_prompt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dictionary", tags=["dictionary"])


@router.post("/define", response_model=DefineResponse)
async def define_word(request: DefineRequest):
    """Get word definition and lemma using OpenAI API.
    
    Args:
        word: The word to define
        sentence: The sentence containing the word (for context)
        language: The language of the sentence
    
    Returns:
        DefineResponse with lemma and definition
    """
    prompt = build_word_definition_prompt(
        language=request.language,
        sentence=request.sentence,
        word=request.word
    )
    
    try:
        content = await call_openai_chat(
            prompt=prompt,
            model="gpt-4.1-mini",
            max_tokens=200,
            temperature=0
        )
        
        # Parse JSON response
        result = parse_json_from_content(content)
        
        if result:
            lemma = result.get("lemma", request.word)
            definition = result.get("definition", "Definition not found")
            
            logger.info("Word definition extracted", extra={
                "word": request.word,
                "lemma": lemma,
                "language": request.language
            })
            
            return DefineResponse(lemma=lemma, definition=definition)
        else:
            # Fallback: return content as definition if JSON parsing fails
            logger.warning("Failed to parse JSON, using content as definition", extra={
                "word": request.word,
                "content_preview": content[:200]
            })
            return DefineResponse(
                lemma=request.word,
                definition=content if len(content) < 500 else "Definition not found"
            )
    
    except Exception as e:
        status_code, detail = get_llm_error_response(e)
        logger.error("LLM error", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(status_code=status_code, detail=detail)
