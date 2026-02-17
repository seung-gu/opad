"""Dictionary lookup service — orchestrates the hybrid lookup pipeline.

Pipeline: Step 1 (lemma extraction) → Dictionary API → Step 2 (sense selection)
Falls back to full LLM when the hybrid pipeline fails.
Token usage is tracked per LLM call via token_usage_service.
"""

import logging
from typing import Any

from adapter.external.free_dictionary import extract_entry_metadata
from port.dictionary import DictionaryPort
from port.llm import LLMPort
from port.token_usage_repository import TokenUsageRepository
from services.token_usage_service import track_llm_usage
from utils.language_metadata import get_language_code
from utils.lemma_extraction import extract_lemma
from utils.llm import parse_json_from_content
from utils.prompts import build_word_definition_prompt
from utils.sense_selection import select_best_sense

logger = logging.getLogger(__name__)

# Token limits for full LLM fallback
FULL_PROMPT_MAX_TOKENS = 2000

# Default messages
DEFAULT_DEFINITION = "Definition not found"


async def lookup(
    word: str,
    sentence: str,
    language: str,
    dictionary: DictionaryPort,
    llm: LLMPort,
    token_usage_repo: TokenUsageRepository | None = None,
    user_id: str | None = None,
    article_id: str | None = None,
    reduced_llm_model: str = "openai/gpt-4.1-mini",
    full_llm_model: str = "openai/gpt-4.1-mini",
) -> dict[str, Any]:
    """Perform dictionary lookup using hybrid approach.

    Falls back to full LLM when hybrid pipeline fails.
    Token usage is tracked per LLM call if token_usage_repo is provided.

    Returns:
        result_dict with keys: lemma, definition, related_words, level,
        pos, gender, phonetics, conjugations, examples, source.
    """
    hybrid_result = await _perform_hybrid_lookup(
        word, sentence, language, dictionary, llm,
        reduced_llm_model, full_llm_model,
        token_usage_repo, user_id, article_id,
    )
    if hybrid_result is not None:
        return hybrid_result
    return await _fallback_full_llm(
        word, sentence, language, llm, full_llm_model,
        token_usage_repo, user_id, article_id,
    )


# ------------------------------------------------------------------
# Hybrid pipeline
# ------------------------------------------------------------------

async def _perform_hybrid_lookup(
    word: str,
    sentence: str,
    language: str,
    dictionary: DictionaryPort,
    llm: LLMPort,
    reduced_llm_model: str,
    full_llm_model: str,
    token_usage_repo: TokenUsageRepository | None,
    user_id: str | None,
    article_id: str | None,
) -> dict[str, Any] | None:
    """Execute the hybrid pipeline: lemma → API → sense selection."""
    # Step 1: Lemma extraction
    lemma_data, lemma_stats = await extract_lemma(
        word, sentence, language, llm, model=reduced_llm_model,
    )
    if lemma_data is None:
        return None

    # Track lemma extraction usage
    if token_usage_repo and user_id:
        track_llm_usage(
            token_usage_repo, lemma_stats, user_id,
            operation="dictionary_search",
            article_id=article_id,
            metadata={"word": word, "language": language, "step": "lemma_extraction"},
        )

    lemma = lemma_data.get("lemma", word)
    logger.info("Lemma extracted", extra={
        "word": word, "lemma": lemma,
        "related_words": lemma_data.get("related_words"),
        "level": lemma_data.get("level"),
    })

    # Step 2: Dictionary API
    entries = await dictionary.fetch(word=lemma, language=language)
    if not entries:
        logger.info("Dictionary API unavailable, falling back to full LLM",
                     extra={"word": word, "lemma": lemma})
        return None

    # Step 3: Sense selection
    sense = await select_best_sense(
        sentence, word, entries, llm, model=full_llm_model,
    )

    # Track sense selection usage
    if token_usage_repo and user_id:
        track_llm_usage(
            token_usage_repo, sense.stats, user_id,
            operation="dictionary_search",
            article_id=article_id,
            metadata={"word": word, "language": language, "step": "sense_selection"},
        )

    # Extract metadata from selected entry
    language_code = get_language_code(language)
    selected_entry = entries[sense.entry_idx]
    metadata = extract_entry_metadata(selected_entry, language_code) if language_code else {}

    # Build final result
    result = _build_result(lemma_data, metadata, sense, word)

    logger.info("Word definition extracted (hybrid)", extra={
        "word": word, "lemma": result["lemma"],
        "related_words": result["related_words"], "pos": result["pos"],
        "gender": result["gender"], "level": result["level"],
        "language": language, "source": "hybrid",
    })
    return result


# ------------------------------------------------------------------
# Full LLM fallback
# ------------------------------------------------------------------

async def _fallback_full_llm(
    word: str,
    sentence: str,
    language: str,
    llm: LLMPort,
    full_llm_model: str,
    token_usage_repo: TokenUsageRepository | None,
    user_id: str | None,
    article_id: str | None,
) -> dict[str, Any]:
    """Fallback to full LLM when hybrid pipeline fails."""
    prompt = build_word_definition_prompt(
        language=language, sentence=sentence, word=word,
    )

    content, stats = await llm.call(
        messages=[{"role": "user", "content": prompt}],
        model=full_llm_model,
        max_tokens=FULL_PROMPT_MAX_TOKENS,
        temperature=0,
    )

    # Track full LLM fallback usage
    if token_usage_repo and user_id:
        track_llm_usage(
            token_usage_repo, stats, user_id,
            operation="dictionary_search",
            article_id=article_id,
            metadata={"word": word, "step": "full_llm_fallback"},
        )

    result = parse_json_from_content(content)
    if result:
        logger.info("Word definition extracted (full LLM fallback)", extra={
            "word": word, "lemma": result.get("lemma", word),
            "language": language, "source": "llm",
        })
        return {
            "lemma": result.get("lemma", word),
            "definition": result.get("definition", DEFAULT_DEFINITION),
            "related_words": result.get("related_words"),
            "pos": result.get("pos"),
            "gender": result.get("gender"),
            "phonetics": None,
            "conjugations": result.get("conjugations"),
            "level": result.get("level"),
            "examples": None,
            "source": "llm",
        }

    logger.warning("Failed to parse JSON in fallback", extra={
        "word": word, "content_preview": content[:200] if content else None,
    })
    return {
        "lemma": word,
        "definition": DEFAULT_DEFINITION,
        "related_words": None,
        "pos": None,
        "gender": None,
        "phonetics": None,
        "conjugations": None,
        "level": None,
        "examples": None,
        "source": "llm",
    }


# ------------------------------------------------------------------
# Result building helpers
# ------------------------------------------------------------------

def _build_result(
    lemma_data: dict[str, Any],
    metadata: dict[str, Any],
    sense,
    word: str,
) -> dict[str, Any]:
    """Merge lemma extraction, API metadata, and sense selection into result dict."""
    conjugations = _extract_conjugations(metadata.get("forms"))

    return {
        "lemma": lemma_data.get("lemma", word),
        "definition": sense.definition or DEFAULT_DEFINITION,
        "related_words": lemma_data.get("related_words"),
        "level": lemma_data.get("level"),
        "pos": metadata.get("pos"),
        "gender": metadata.get("gender"),
        "phonetics": metadata.get("phonetics"),
        "conjugations": conjugations,
        "examples": sense.examples,
        "source": "hybrid",
    }


def _extract_conjugations(forms: dict[str, str] | None) -> dict[str, str] | None:
    """Extract conjugations from API forms."""
    if not forms:
        return None
    conjugations: dict[str, str] = {}
    for key in ("present", "past", "participle", "auxiliary", "genitive", "plural"):
        if forms.get(key):
            conjugations[key] = forms[key]
    return conjugations or None
