"""Dictionary API routes for word definitions.

This module handles word definition requests using OpenAI API:
- POST /dictionary/define: Get word definition and lemma from sentence context
- GET /dictionary/stats: Get vocabulary collection statistics
"""

import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from api.models import DefineRequest, DefineResponse, VocabularyRequest, VocabularyResponse
from utils.llm import call_openai_chat, parse_json_from_content, get_llm_error_response
from utils.prompts import build_word_definition_prompt
from utils.mongodb import save_vocabulary, get_vocabularies, delete_vocabulary, get_mongodb_client, get_vocabulary_word_counts

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
            related_words = result.get("related_words", None)
            
            logger.info("Word definition extracted", extra={
                "word": request.word,
                "lemma": lemma,
                "related_words": related_words,
                "language": request.language
            })
            
            return DefineResponse(lemma=lemma, definition=definition, related_words=related_words)
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


@router.post("/vocabularies", response_model=VocabularyResponse)
async def add_vocabulary(request: VocabularyRequest):
    """Add a word to vocabulary list.
    
    Args:
        request: Vocabulary request with word, lemma, definition, etc.
    
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
        span_id=request.span_id
    )
    
    if not vocabulary_id:
        raise HTTPException(status_code=500, detail="Failed to save vocabulary")
    
    # Get the saved vocabulary to return
    vocabularies = get_vocabularies(article_id=request.article_id)
    vocabulary = next((v for v in vocabularies if v['id'] == vocabulary_id), None)
    
    if not vocabulary:
        raise HTTPException(status_code=500, detail="Vocabulary saved but not found")
    
    logger.info("Vocabulary added", extra={
        "vocabularyId": vocabulary_id,
        "articleId": request.article_id,
        "lemma": request.lemma
    })
    
    return VocabularyResponse(**vocabulary)


@router.get("/vocabularies", response_model=list[VocabularyResponse])
async def get_vocabularies_list(article_id: str | None = None):
    """Get vocabulary list.
    
    Args:
        article_id: Optional article ID to filter vocabularies
    
    Returns:
        List of vocabularies
    """
    vocabularies = get_vocabularies(article_id=article_id)
    
    logger.info("Vocabularies retrieved", extra={
        "count": len(vocabularies),
        "articleId": article_id
    })
    
    return [VocabularyResponse(**v) for v in vocabularies]


@router.delete("/vocabularies/{vocabulary_id}")
async def delete_vocabulary_word(vocabulary_id: str):
    """Delete a vocabulary word.
    
    Args:
        vocabulary_id: Vocabulary ID to delete
    
    Returns:
        Success message
    """
    success = delete_vocabulary(vocabulary_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Vocabulary not found")
    
    logger.info("Vocabulary deleted", extra={"vocabularyId": vocabulary_id})
    
    return {"message": "Vocabulary deleted successfully"}


def _check_mongodb_connection() -> None:
    """Check MongoDB connection and raise if unavailable."""
    if not get_mongodb_client():
        raise HTTPException(status_code=503, detail="Database service unavailable")


@router.get("/stats")
async def get_vocabulary_list_endpoint(language: str | None = None):
    """Get vocabulary word list grouped by language.
    
    Args:
        language: Optional language filter
        
    Returns HTML page showing vocabulary words grouped by language.
    """
    _check_mongodb_connection()
    
    word_counts = get_vocabulary_word_counts(language=language)
    
    return _render_vocabulary_list_html(word_counts, language=language)


def _render_vocabulary_list_html(word_counts: list[dict], language: str | None = None) -> HTMLResponse:
    """Render vocabulary word list as HTML page."""
    # Group by language
    by_language: dict[str, list[dict]] = {}
    for item in word_counts:
        lang = item['language']
        if lang not in by_language:
            by_language[lang] = []
        by_language[lang].append(item)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Vocabulary List - OPAD</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-50 p-8">
        <div class="max-w-6xl mx-auto">
            <div class="mb-6">
                <h1 class="text-3xl font-bold text-gray-900 mb-2">Vocabulary List</h1>
                <p class="text-gray-600">Words saved by users, grouped by language</p>
            </div>

            <div class="mb-4">
                <a href="/stats" class="text-blue-600 hover:text-blue-800 underline">← Back to Statistics</a>
            </div>
"""
    
    if not by_language:
        html += """
            <div class="bg-white rounded-lg shadow-lg p-8 text-center">
                <p class="text-gray-500 text-lg">No vocabulary words found.</p>
            </div>
        """
    else:
        for lang, words in sorted(by_language.items()):
            html += f"""
            <div class="bg-white rounded-lg shadow-lg overflow-hidden mb-6">
                <div class="bg-gradient-to-r from-emerald-600 to-emerald-700 text-white p-4">
                    <h2 class="text-2xl font-semibold">{lang}</h2>
                    <p class="text-emerald-100">{len(words)} unique words</p>
                </div>
                <div class="p-6">
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
"""
            for word in words:
                count = word['count']
                lemma = word['lemma']
                article_count = len(word['article_ids'])
                html += f"""
                        <div class="bg-gray-50 rounded-lg p-4 border border-gray-200">
                            <div class="flex items-center justify-between mb-2">
                                <span class="text-lg font-semibold text-gray-900">{lemma}</span>
                                <span class="text-sm font-medium text-emerald-600 bg-emerald-100 px-2 py-1 rounded">
                                    {count} time{'s' if count > 1 else ''}
                                </span>
                            </div>
                            <div class="text-xs text-gray-500">
                                in {article_count} article{'s' if article_count > 1 else ''}
                            </div>
                        </div>
"""
            html += """
                    </div>
                </div>
            </div>
"""
    
    html += """
            <div class="mt-6 text-center">
                <button onclick="window.location.reload()" class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                    Refresh List
                </button>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html)
