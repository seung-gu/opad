"""Sense selection module — Step 2 of the dictionary lookup pipeline.

Given dictionary entries (from the dictionary port), selects the best
entry/sense/subsense that matches the word usage in context, using an LLM.
"""

import logging
from typing import Any

from domain.model.token_usage import LLMCallResult
from domain.model.vocabulary import SenseResult
from port.dictionary import DictionaryPort
from port.llm import LLMPort

logger = logging.getLogger(__name__)

DEFAULT_LABEL = "0.0"


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

async def select_best_sense(
    sentence: str,
    word: str,
    entries: list[dict[str, Any]],
    dictionary: DictionaryPort,
    llm: LLMPort,
    model: str = "openai/gpt-4.1-mini",
) -> tuple[SenseResult, str, LLMCallResult | None]:
    """Select the best sense from dictionary entries for a word in context.

    Returns:
        (SenseResult, label, LLMCallResult | None).
    """
    if not entries:
        return SenseResult(), DEFAULT_LABEL, None

    return await _pick_sense(sentence, word, entries, dictionary, llm, model)


# ---------------------------------------------------------------------------
# LLM sense selection
# ---------------------------------------------------------------------------

async def _pick_sense(
    sentence: str,
    word: str,
    entries: list[dict[str, Any]],
    dictionary: DictionaryPort,
    llm: LLMPort,
    model: str,
) -> tuple[SenseResult, str, LLMCallResult | None]:
    """Select best sense via LLM and return complete SenseResult.

    Skips LLM if build_sense_listing returns None (trivial).
    """
    listing = dictionary.build_sense_listing(entries)
    if listing is None:
        return dictionary.get_sense(entries, DEFAULT_LABEL), DEFAULT_LABEL, None

    prompt = _build_sense_prompt(sentence, word, listing)

    try:
        content, stats = await llm.call(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0,
            timeout=15,
            max_tokens=10,
        )
        return dictionary.get_sense(entries, content), content, stats
    except Exception as e:
        logger.warning(
            "Failed to select sense via LLM, using defaults",
            extra={"error": str(e)},
        )

    return dictionary.get_sense(entries, DEFAULT_LABEL), DEFAULT_LABEL, None


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def _build_sense_prompt(sentence: str, word: str, listing: str) -> str:
    """Wrap a sense listing with LLM instructions for sense selection."""
    return f"""Sentence: "{sentence}"
Word: "{word}"

Which definition best matches the word usage in this sentence?
Reply with the number only (e.g. 1.0 or 0.0.1 for a subsense).

{listing}"""
