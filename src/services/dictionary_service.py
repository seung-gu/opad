"""Dictionary lookup service with hybrid LLM + API approach.

This service encapsulates all dictionary lookup logic, separating
business logic from HTTP handling in the routes layer.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

from utils.dictionary_api import fetch_from_free_dictionary_api, DictionaryAPIResult
from utils.llm import TokenUsageStats, call_llm_with_tracking, parse_json_from_content
from utils.prompts import build_word_definition_prompt, build_reduced_word_definition_prompt

logger = logging.getLogger(__name__)

# Token limits for LLM calls
REDUCED_PROMPT_MAX_TOKENS = 200
FULL_PROMPT_MAX_TOKENS = 2000

# Default messages
DEFAULT_DEFINITION = "Definition not found"

# Languages with accurate IPA phonetics from Free Dictionary API
PHONETICS_SUPPORTED_LANGUAGES = {"English"}


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
    """Service for dictionary lookups using hybrid LLM + API approach.

    This service combines:
    1. LLM (reduced prompt): Extracts lemma, related_words, and CEFR level
    2. Free Dictionary API: Provides definition, POS, pronunciation, and forms

    Falls back to full LLM when API is unavailable.

    Attributes:
        reduced_llm_model: Model for reduced prompt calls.
        full_llm_model: Model for full fallback calls.
    """

    def __init__(
        self,
        reduced_llm_model: str = "openai/gpt-4.1-mini",
        full_llm_model: str = "openai/gpt-4.1-mini"
    ):
        """Initialize dictionary service.

        Args:
            reduced_llm_model: Model for reduced prompt (lemma extraction).
            full_llm_model: Model for full fallback (all fields).
        """
        self.reduced_llm_model = reduced_llm_model
        self.full_llm_model = full_llm_model
        self._last_stats: TokenUsageStats | None = None

    @property
    def last_token_stats(self) -> TokenUsageStats | None:
        """Get token usage stats from the last lookup."""
        return self._last_stats

    async def lookup(self, request: LookupRequest) -> LookupResult:
        """Perform dictionary lookup using hybrid approach.

        Args:
            request: Lookup request with word, sentence, and language.

        Returns:
            LookupResult with merged data from LLM and API.
        """
        # Try hybrid approach first
        hybrid_result = await self._perform_hybrid_lookup(request)

        if hybrid_result is not None:
            return hybrid_result

        # Fall back to full LLM
        return await self._fallback_full_llm(request)

    async def _perform_hybrid_lookup(self, request: LookupRequest) -> LookupResult | None:
        """Perform hybrid lookup combining LLM and Dictionary API.

        Args:
            request: Lookup request.

        Returns:
            LookupResult on success, None if should fall back to full LLM.
        """
        # Step 1: Get lemma and level from LLM
        llm_data, stats = await self._call_llm_reduced(request)

        if llm_data is None:
            return None

        # Step 2: Get definition and forms from Dictionary API
        lemma = llm_data.get("lemma", request.word)
        related_words = llm_data.get("related_words", [])

        logger.info("LLM reduced response", extra={
            "word": request.word,
            "lemma": lemma,
            "related_words": related_words,
            "level": llm_data.get("level"),
            "api_lookup": lemma
        })
        dict_data = await fetch_from_free_dictionary_api(
            word=lemma,
            language=request.language
        )

        if dict_data is None:
            logger.info(
                "Dictionary API returned None, falling back to full LLM",
                extra={"word": request.word, "lemma": lemma}
            )
            return None

        # Select best sense from available senses
        sense_stats = None
        if dict_data.all_senses:
            selected_sense, sense_stats = await self._select_best_sense(
                request.sentence,
                dict_data.all_senses
            )
            dict_data.definition = selected_sense.get("definition", DEFAULT_DEFINITION)
            dict_data.examples = self._extract_examples_from_sense(selected_sense)
        else:
            logger.info(
                "Dictionary API missing senses, falling back to full LLM",
                extra={"word": request.word, "lemma": lemma}
            )
            return None

        # Store stats for tracking (accumulate sense selection tokens)
        if stats:
            if sense_stats:
                stats = TokenUsageStats(
                    model=stats.model,
                    prompt_tokens=stats.prompt_tokens + sense_stats.prompt_tokens,
                    completion_tokens=stats.completion_tokens + sense_stats.completion_tokens,
                    total_tokens=stats.total_tokens + sense_stats.total_tokens,
                    estimated_cost=stats.estimated_cost + sense_stats.estimated_cost,
                    provider=stats.provider,
                )
            self._last_stats = stats

        # Merge results
        result = self._merge_results(llm_data, dict_data, request.word)

        # Apply language filters
        result = self._apply_language_filters(result, request.language)

        logger.info("Word definition extracted (hybrid)", extra={
            "word": request.word,
            "lemma": result.lemma,
            "related_words": result.related_words,
            "pos": result.pos,
            "gender": result.gender,
            "level": result.level,
            "language": request.language,
            "source": "hybrid"
        })

        return result

    async def _call_llm_reduced(
        self,
        request: LookupRequest
    ) -> tuple[dict[str, Any] | None, Any]:
        """Call LLM with reduced prompt for lemma and level only.

        Args:
            request: Lookup request.

        Returns:
            Tuple of (parsed result dict, token stats) or (None, None) on error.
        """
        try:
            prompt = build_reduced_word_definition_prompt(
                language=request.language,
                sentence=request.sentence,
                word=request.word
            )

            content, stats = await call_llm_with_tracking(
                messages=[{"role": "user", "content": prompt}],
                model=self.reduced_llm_model,
                max_tokens=REDUCED_PROMPT_MAX_TOKENS,
                temperature=0
            )

            result = parse_json_from_content(content)

            if result is None:
                logger.warning(
                    "Failed to parse JSON from LLM reduced prompt response",
                    extra={
                        "word": request.word,
                        "language": request.language,
                        "content_preview": content[:200] if content else None
                    }
                )

            return result, stats

        except Exception as e:
            logger.error(
                "Error in LLM reduced call",
                extra={
                    "word": request.word,
                    "language": request.language,
                    "error": str(e)
                },
                exc_info=True
            )
            return None, None

    async def _fallback_full_llm(self, request: LookupRequest) -> LookupResult:
        """Fallback to full LLM search when hybrid approach fails.

        Args:
            request: Lookup request.

        Returns:
            LookupResult with all fields from LLM.

        Raises:
            Exception: On LLM errors.
        """
        prompt = build_word_definition_prompt(
            language=request.language,
            sentence=request.sentence,
            word=request.word
        )

        content, stats = await call_llm_with_tracking(
            messages=[{"role": "user", "content": prompt}],
            model=self.full_llm_model,
            max_tokens=FULL_PROMPT_MAX_TOKENS,
            temperature=0
        )

        # Store stats for tracking
        self._last_stats = stats

        result = parse_json_from_content(content)

        if result:
            logger.info("Word definition extracted (full LLM fallback)", extra={
                "word": request.word,
                "lemma": result.get("lemma", request.word),
                "related_words": result.get("related_words"),
                "pos": result.get("pos"),
                "gender": result.get("gender"),
                "level": result.get("level"),
                "language": request.language,
                "source": "llm"
            })

            return LookupResult(
                lemma=result.get("lemma", request.word),
                definition=result.get("definition", DEFAULT_DEFINITION),
                related_words=result.get("related_words"),
                pos=result.get("pos"),
                gender=result.get("gender"),
                conjugations=result.get("conjugations"),
                level=result.get("level"),
                source="llm"
            )

        # Last resort: use raw content as definition
        logger.warning("Failed to parse JSON in fallback, using content", extra={
            "word": request.word,
            "content_preview": content[:200]
        })

        return LookupResult(
            lemma=request.word,
            definition=DEFAULT_DEFINITION,
            source="llm"
        )

    def _merge_results(
        self,
        llm_data: dict[str, Any],
        dict_data: DictionaryAPIResult,
        word: str
    ) -> LookupResult:
        """Merge LLM and Dictionary API results.

        Args:
            llm_data: Parsed LLM response.
            dict_data: Dictionary API result.
            word: Original word for fallback.

        Returns:
            Merged LookupResult.
        """
        conjugations = self._extract_conjugations(dict_data.forms)

        return LookupResult(
            lemma=llm_data.get("lemma", word),
            definition=dict_data.definition or DEFAULT_DEFINITION,
            related_words=llm_data.get("related_words"),
            level=llm_data.get("level"),
            pos=dict_data.pos,
            gender=dict_data.gender,
            phonetics=dict_data.phonetics,
            conjugations=conjugations,
            examples=dict_data.examples,
            source="hybrid"
        )

    def _extract_conjugations(self, forms: dict[str, str] | None) -> dict[str, str] | None:
        """Extract conjugations from API forms.

        Args:
            forms: Forms dict from API response.

        Returns:
            Conjugations dict or None.
        """
        if not forms:
            return None

        conjugations: dict[str, str] = {}

        # Copy relevant form fields
        for key in ("present", "past", "participle", "auxiliary", "genitive", "plural"):
            if forms.get(key):
                conjugations[key] = forms[key]

        return conjugations or None

    def _apply_language_filters(self, result: LookupResult, language: str) -> LookupResult:
        """Apply language-specific post-processing filters.

        Args:
            result: Lookup result.
            language: Language name.

        Returns:
            Filtered result.
        """
        if language not in PHONETICS_SUPPORTED_LANGUAGES:
            result.phonetics = None
        return result

    async def _select_best_sense(
        self,
        sentence: str,
        senses: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], TokenUsageStats | None]:
        """Select the best sense based on sentence context using LLM.

        Args:
            sentence: The sentence containing the word.
            senses: List of sense dictionaries from API.

        Returns:
            Tuple of (best matching sense dict, token usage stats or None).
        """
        if not senses:
            return {"definition": DEFAULT_DEFINITION}, None

        if len(senses) == 1:
            return senses[0], None

        # Build options (limit to 6 for context length)
        options = []
        for i, sense in enumerate(senses[:6]):
            defn = sense.get("definition", "")
            options.append(f"{i+1}. {defn}")

        prompt = f"""Sentence: "{sentence}"

Which definition best matches the word usage in this sentence?
Reply with the number only.

{chr(10).join(options)}"""

        try:
            content, sense_stats = await call_llm_with_tracking(
                messages=[{"role": "user", "content": prompt}],
                model=self.full_llm_model,
                temperature=0,
                timeout=15,
                max_tokens=10
            )
            match = re.search(r"\d+", content)
            if match:
                selected = int(match.group()) - 1
                if 0 <= selected < len(senses):
                    return senses[selected], sense_stats
            return senses[0], sense_stats
        except Exception as e:
            logger.warning(
                "Failed to select sense via LLM, using first",
                extra={"error": str(e)}
            )

        return senses[0], None

    def _extract_examples_from_sense(self, sense: dict[str, Any], max_examples: int = 3) -> list[str] | None:
        """Extract examples from a single sense.

        Args:
            sense: Sense dictionary from API.
            max_examples: Maximum number of examples.

        Returns:
            List of example strings or None.
        """
        examples = []
        for example in sense.get("examples", [])[:max_examples]:
            if isinstance(example, str):
                examples.append(example)
            elif isinstance(example, dict) and "text" in example:
                examples.append(example["text"])
        return examples if examples else None
