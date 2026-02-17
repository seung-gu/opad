"""Sense selection module — Step 2 of the dictionary lookup pipeline.

Given dictionary entries (from the Free Dictionary API), selects the best
entry/sense/subsense that matches the word usage in context, using an LLM.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

from port.llm import LLMPort
from domain.model.token_usage import LLMCallResult

logger = logging.getLogger(__name__)


@dataclass
class SenseResult:
    """Result of sense selection."""
    entry_idx: int = 0
    sense_idx: int = 0
    subsense_idx: int = -1
    definition: str = ""
    examples: list[str] | None = None
    stats: LLMCallResult | None = None


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

async def select_best_sense(
    sentence: str,
    word: str,
    entries: list[dict[str, Any]],
    llm: LLMPort,
    model: str = "openai/gpt-4.1-mini",
) -> SenseResult:
    """Select the best sense from dictionary entries for a word in context.

    Args:
        sentence: The sentence containing the word.
        word: The word being looked up.
        entries: All entries from the dictionary API.
        llm: LLM port for API calls.
        model: LLM model identifier for sense selection.

    Returns:
        SenseResult with selected indices, definition, examples, and stats.
    """
    if not entries:
        return SenseResult()

    # Select entry/sense/subsense via LLM (or skip if trivial)
    ei, si, ssi, stats = await _select_entry_sense(sentence, word, entries, llm, model)

    # Extract definition and examples from the selected sense
    definition, selected_sense = _get_definition_from_selection(entries[ei], si, ssi)
    examples = _extract_examples(selected_sense) if selected_sense else None

    return SenseResult(
        entry_idx=ei,
        sense_idx=si,
        subsense_idx=ssi,
        definition=definition,
        examples=examples,
        stats=stats,
    )


# ---------------------------------------------------------------------------
# LLM sense selection
# ---------------------------------------------------------------------------

async def _select_entry_sense(
    sentence: str,
    word: str,
    entries: list[dict[str, Any]],
    llm: LLMPort,
    model: str,
) -> tuple[int, int, int, LLMCallResult | None]:
    """Select best entry/sense/subsense indices via LLM.

    Skips LLM if only one entry with one sense and no subsenses.
    """
    # Skip LLM if trivial (single entry, single sense, no subsenses)
    total_senses = sum(len(e.get("senses", [])) for e in entries)
    total_subsenses = sum(
        len(s.get("subsenses", []))
        for e in entries for s in e.get("senses", [])
    )
    if len(entries) == 1 and total_senses <= 1 and total_subsenses == 0:
        return 0, 0, -1, None

    prompt = _build_sense_prompt(sentence, word, entries)

    try:
        content, stats = await llm.call(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0,
            timeout=15,
            max_tokens=10,
        )
        ei, si, ssi = _parse_sense_response(content, entries)
        return ei, si, ssi, stats
    except Exception as e:
        logger.warning(
            "Failed to select sense via LLM, using defaults",
            extra={"error": str(e)},
        )

    return 0, 0, -1, None


# ---------------------------------------------------------------------------
# Prompt building & response parsing
# ---------------------------------------------------------------------------

def _build_sense_prompt(
    sentence: str,
    word: str,
    entries: list[dict[str, Any]],
) -> str:
    """Build X.Y.Z format prompt for LLM entry+sense selection."""
    options = []
    for i, entry in enumerate(entries):
        pos = entry.get("partOfSpeech", "unknown")
        options.append(f"entries[{i}] ({pos}):")
        for j, sense in enumerate(entry.get("senses", [])):
            options.append(f"  {i}.{j} {sense.get('definition', '')}")
            for k, sub in enumerate(sense.get("subsenses", [])):
                options.append(f"    {i}.{j}.{k} {sub.get('definition', '')}")

    return f"""Sentence: "{sentence}"
Word: "{word}"

Which definition best matches the word usage in this sentence?
Reply with the number only (e.g. 1.0 or 0.0.1 for a subsense).

{chr(10).join(options)}"""


def _parse_sense_response(
    content: str,
    entries: list[dict[str, Any]],
) -> tuple[int, int, int]:
    """Parse LLM response into (entry_idx, sense_idx, subsense_idx) with clamping."""
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", content)
    if not match:
        return 0, 0, -1

    ei = max(0, min(int(match.group(1)), len(entries) - 1))
    senses = entries[ei].get("senses", [])
    si = max(0, min(int(match.group(2)), len(senses) - 1)) if senses else 0

    ssi = -1
    if match.group(3) is not None and senses:
        subsenses = senses[si].get("subsenses", [])
        ssi = max(0, min(int(match.group(3)), len(subsenses) - 1)) if subsenses else -1

    return ei, si, ssi


# ---------------------------------------------------------------------------
# Definition & examples extraction
# ---------------------------------------------------------------------------

def _get_definition_from_selection(
    entry: dict[str, Any],
    sense_idx: int,
    subsense_idx: int,
) -> tuple[str, dict[str, Any] | None]:
    """Extract definition from selected entry/sense/subsense indices.

    Returns:
        Tuple of (definition_string, selected_sense_dict_or_None).
    """
    senses = entry.get("senses", [])
    if sense_idx >= len(senses):
        return "", None

    sense = senses[sense_idx]
    subsenses = sense.get("subsenses", [])
    if 0 <= subsense_idx < len(subsenses):
        return subsenses[subsense_idx].get("definition", ""), sense
    return sense.get("definition", ""), sense


def _extract_examples(
    sense: dict[str, Any],
    max_examples: int = 3,
) -> list[str] | None:
    """Extract examples from a single sense."""
    examples = []
    for example in sense.get("examples", [])[:max_examples]:
        if isinstance(example, str):
            examples.append(example)
        elif isinstance(example, dict) and "text" in example:
            examples.append(example["text"])
    return examples if examples else None
