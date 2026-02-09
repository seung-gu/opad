"""Dictionary lookup service — orchestrates the hybrid lookup pipeline.

Pipeline: Step 1 (lemma extraction) → Dictionary API → Step 2 (sense selection)
Falls back to full LLM when the hybrid pipeline fails.
"""

import logging
from dataclasses import dataclass
from typing import Any

from utils.dictionary_api import (
    fetch_from_free_dictionary_api,
    DictionaryAPIResult,
    extract_entry_metadata,
    get_language_code,
)
from utils.lemma_extraction import extract_lemma
from utils.sense_selection import select_best_sense
from utils.llm import TokenUsageStats, accumulate_stats, call_llm_with_tracking, parse_json_from_content
from utils.prompts import build_word_definition_prompt

logger = logging.getLogger(__name__)

# Token limits for full LLM fallback
FULL_PROMPT_MAX_TOKENS = 2000

# Default messages
DEFAULT_DEFINITION = "Definition not found"


@dataclass
class LookupRequest:
    """Request for dictionary lookup."""
    word: str
    sentence: str
    language: str
    article_id: str | None = None


@dataclass
class LookupResult:
    """Result from dictionary lookup."""
    lemma: str
    definition: str
    related_words: list[str] | None = None
    level: str | None = None
    pos: str | None = None
    gender: str | None = None
    phonetics: str | None = None
    conjugations: dict[str, str] | None = None
    examples: list[str] | None = None
    source: str = "hybrid"


class DictionaryService:
    """Orchestrates the hybrid dictionary lookup pipeline.

    Pipeline:
        1. Lemma extraction (Stanza for German, LLM for others)
        2. Free Dictionary API (definition, POS, pronunciation, forms)
        3. Sense selection (LLM picks best sense from API entries)

    Falls back to full LLM when pipeline fails.
    """

    def __init__(
        self,
        reduced_llm_model: str = "openai/gpt-4.1-mini",
        full_llm_model: str = "openai/gpt-4.1-mini",
    ):
        self.reduced_llm_model = reduced_llm_model
        self.full_llm_model = full_llm_model
        self._last_stats: TokenUsageStats | None = None

    @property
    def last_token_stats(self) -> TokenUsageStats | None:
        """Get token usage stats from the last lookup."""
        return self._last_stats

    async def lookup(self, request: LookupRequest) -> LookupResult:
        """Perform dictionary lookup using hybrid approach.

        Falls back to full LLM when hybrid pipeline fails.
        """
        hybrid_result = await self._perform_hybrid_lookup(request)
        if hybrid_result is not None:
            return hybrid_result
        return await self._fallback_full_llm(request)

    # ------------------------------------------------------------------
    # Hybrid pipeline
    # ------------------------------------------------------------------

    async def _perform_hybrid_lookup(self, request: LookupRequest) -> LookupResult | None:
        """Execute the hybrid pipeline: lemma → API → sense selection.

        Returns None if any step fails (triggers full LLM fallback).
        """
        # Step 1: Lemma extraction
        lemma_data, lemma_stats = await extract_lemma(
            request.word, request.sentence, request.language,
            model=self.reduced_llm_model,
        )
        if lemma_data is None:
            return None

        lemma = lemma_data.get("lemma", request.word)
        logger.info("Lemma extracted", extra={
            "word": request.word,
            "lemma": lemma,
            "related_words": lemma_data.get("related_words"),
            "level": lemma_data.get("level"),
        })

        # Step 2: Dictionary API
        dict_data = await fetch_from_free_dictionary_api(
            word=lemma, language=request.language,
        )
        if dict_data is None or not dict_data.all_entries:
            logger.info("Dictionary API unavailable, falling back to full LLM",
                        extra={"word": request.word, "lemma": lemma})
            return None

        # Step 3: Sense selection
        sense = await select_best_sense(
            request.sentence, request.word, dict_data.all_entries,
            model=self.full_llm_model,
        )

        # Extract metadata from selected entry
        language_code = get_language_code(request.language)
        selected_entry = dict_data.all_entries[sense.entry_idx]
        if language_code:
            metadata = extract_entry_metadata(selected_entry, language_code)
            dict_data.pos = metadata["pos"]
            dict_data.phonetics = metadata["phonetics"]
            dict_data.forms = metadata["forms"]
            dict_data.gender = metadata["gender"]

        # Accumulate token stats
        self._last_stats = accumulate_stats(lemma_stats, sense.stats)

        # Build final result
        result = self._build_result(lemma_data, dict_data, sense, request.word)

        logger.info("Word definition extracted (hybrid)", extra={
            "word": request.word, "lemma": result.lemma,
            "related_words": result.related_words, "pos": result.pos,
            "gender": result.gender, "level": result.level,
            "language": request.language, "source": "hybrid",
        })
        return result

    # ------------------------------------------------------------------
    # Full LLM fallback
    # ------------------------------------------------------------------

    async def _fallback_full_llm(self, request: LookupRequest) -> LookupResult:
        """Fallback to full LLM when hybrid pipeline fails."""
        prompt = build_word_definition_prompt(
            language=request.language,
            sentence=request.sentence,
            word=request.word,
        )

        content, stats = await call_llm_with_tracking(
            messages=[{"role": "user", "content": prompt}],
            model=self.full_llm_model,
            max_tokens=FULL_PROMPT_MAX_TOKENS,
            temperature=0,
        )
        self._last_stats = stats

        result = parse_json_from_content(content)
        if result:
            logger.info("Word definition extracted (full LLM fallback)", extra={
                "word": request.word,
                "lemma": result.get("lemma", request.word),
                "language": request.language, "source": "llm",
            })
            return LookupResult(
                lemma=result.get("lemma", request.word),
                definition=result.get("definition", DEFAULT_DEFINITION),
                related_words=result.get("related_words"),
                pos=result.get("pos"),
                gender=result.get("gender"),
                conjugations=result.get("conjugations"),
                level=result.get("level"),
                source="llm",
            )

        logger.warning("Failed to parse JSON in fallback", extra={
            "word": request.word, "content_preview": content[:200],
        })
        return LookupResult(
            lemma=request.word,
            definition=DEFAULT_DEFINITION,
            source="llm",
        )

    # ------------------------------------------------------------------
    # Result building helpers
    # ------------------------------------------------------------------

    def _build_result(
        self,
        lemma_data: dict[str, Any],
        dict_data: DictionaryAPIResult,
        sense,
        word: str,
    ) -> LookupResult:
        """Merge lemma extraction, API data, and sense selection into final result."""
        conjugations = _extract_conjugations(dict_data.forms)

        return LookupResult(
            lemma=lemma_data.get("lemma", word),
            definition=sense.definition or DEFAULT_DEFINITION,
            related_words=lemma_data.get("related_words"),
            level=lemma_data.get("level"),
            pos=dict_data.pos,
            gender=dict_data.gender,
            phonetics=dict_data.phonetics,
            conjugations=conjugations,
            examples=sense.examples,
            source="hybrid",
        )


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------

def _extract_conjugations(forms: dict[str, str] | None) -> dict[str, str] | None:
    """Extract conjugations from API forms."""
    if not forms:
        return None
    conjugations: dict[str, str] = {}
    for key in ("present", "past", "participle", "auxiliary", "genitive", "plural"):
        if forms.get(key):
            conjugations[key] = forms[key]
    return conjugations or None


