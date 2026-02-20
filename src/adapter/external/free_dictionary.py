"""Free Dictionary API adapter.

Implements DictionaryPort by fetching entries from the Free Dictionary API.
Also provides entry parsing utilities (metadata, phonetics, forms, gender).

API Documentation: https://freedictionaryapi.com
Supported languages: German (de), English (en), French (fr), Spanish (es)
"""

import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from domain.model.vocabulary import GrammaticalInfo, SenseResult
from utils.language_metadata import (
    GENDER_MAP, REFLEXIVE_PREFIXES, REFLEXIVE_SUFFIXES, PHONETICS_SUPPORTED,
    get_language_code,
)

logger = logging.getLogger(__name__)

FREE_DICTIONARY_API_BASE_URL = "https://freedictionaryapi.com/api/v1/entries"
API_TIMEOUT_SECONDS = 5.0


# ── Internal sense addressing ────────────────────────────────


@dataclass(frozen=True)
class _SenseIndex:
    """Adapter-internal addressing for Free Dictionary entry/sense/subsense."""
    entry: int = 0
    sense: int = 0
    subsense: int = -1

    @classmethod
    def from_label(cls, text: str) -> "_SenseIndex":
        match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
        if not match:
            return cls()
        return cls(
            entry=int(match.group(1)),
            sense=int(match.group(2)),
            subsense=int(match.group(3)) if match.group(3) else -1,
        )


# ── Adapter ──────────────────────────────────────────────────


class FreeDictionaryAdapter:
    """Adapter that fetches dictionary entries from the Free Dictionary API."""

    def build_sense_listing(self, entries: list[dict[str, Any]]) -> str | None:
        if _is_trivial(entries):
            return None
        return _format_sense_listing(entries)

    def get_sense(
        self, entries: list[dict[str, Any]], label: str,
    ) -> SenseResult:
        index = _SenseIndex.from_label(label)
        clamped = _clamp_index(entries, index)
        definition, sense_dict = _read_definition(entries[clamped.entry], clamped.sense, clamped.subsense)
        examples = _read_examples(sense_dict) if sense_dict else None
        return SenseResult(definition=definition, examples=examples)

    def extract_grammar(
        self, entries: list[dict[str, Any]], label: str, language: str,
    ) -> GrammaticalInfo:
        language_code = get_language_code(language)
        if not language_code:
            return GrammaticalInfo()
        index = _SenseIndex.from_label(label)
        ei = max(0, min(index.entry, len(entries) - 1))
        return extract_entry_metadata(entries[ei], language_code)

    async def fetch(self, word: str, language: str) -> list[dict] | None:
        """Fetch dictionary entries for a word.

        Args:
            word: The word to look up.
            language: Full language name (e.g., "German", "English").

        Returns:
            List of entry dicts, or None on error / unsupported language.
        """
        language_code = get_language_code(language)

        if not language_code:
            logger.debug(
                "Language not supported by Free Dictionary API",
                extra={"language": language},
            )
            return None

        # Strip reflexive pronouns for API lookup (e.g., "sich gewöhnen" -> "gewöhnen")
        lookup_word = _strip_reflexive_pronoun(word, language_code)
        url = f"{FREE_DICTIONARY_API_BASE_URL}/{language_code}/{quote(lookup_word, safe='')}"

        try:
            async with httpx.AsyncClient(timeout=API_TIMEOUT_SECONDS) as client:
                response = await _fetch_with_retry(client, url)

                if response.status_code == 404:
                    logger.debug(
                        "Word not found in Free Dictionary API",
                        extra={"word": word, "language": language},
                    )
                    return None

                response.raise_for_status()
                data = response.json()

                if not isinstance(data, dict):
                    logger.warning(
                        "Unexpected response type from Free Dictionary API",
                        extra={"word": word, "language": language, "type": type(data).__name__},
                    )
                    return None

                entries = data.get("entries", [])
                if not entries:
                    logger.debug(
                        "Free Dictionary API returned no entries",
                        extra={"word": word, "language": language},
                    )
                    return None

                logger.debug(
                    "Free Dictionary API lookup successful",
                    extra={"word": word, "language": language, "entry_count": len(entries)},
                )
                return entries

        except httpx.HTTPStatusError as e:
            logger.warning(
                "Free Dictionary API HTTP error",
                extra={"word": word, "language": language, "status_code": e.response.status_code},
            )
            return None
        except httpx.RequestError as e:
            logger.warning(
                "Free Dictionary API request error",
                extra={"word": word, "language": language, "error_type": type(e).__name__},
            )
            return None
        except Exception as e:
            logger.error(
                "Unexpected error calling Free Dictionary API",
                extra={"word": word, "language": language, "error": str(e)},
                exc_info=True,
            )
            return None


# ── HTTP helpers ─────────────────────────────────────────────


@retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True,
)
async def _fetch_with_retry(client: httpx.AsyncClient, url: str) -> httpx.Response:
    """Fetch URL with automatic retry on transient failures."""
    return await client.get(url)


def _strip_reflexive_pronoun(word: str, language_code: str) -> str:
    """Strip reflexive pronouns from verb lemmas for API lookup."""
    word_lower = word.lower()
    for prefix in REFLEXIVE_PREFIXES.get(language_code, []):
        if word_lower.startswith(prefix):
            return word[len(prefix):]
    for suffix in REFLEXIVE_SUFFIXES.get(language_code, []):
        if word_lower.endswith(suffix):
            return word[:-2]
    return word


# ── Entry metadata extraction ────────────────────────────────


def extract_entry_metadata(entry: dict[str, Any], language_code: str) -> GrammaticalInfo:
    """Extract grammatical metadata from a single dictionary entry.

    Args:
        entry: A single entry dict from API response.
        language_code: ISO 639-1 language code.

    Returns:
        GrammaticalInfo domain object with pos, gender, phonetics, conjugations.
    """
    pos = entry.get("partOfSpeech")
    phonetics = _extract_phonetics(entry) if language_code in PHONETICS_SUPPORTED else None
    forms = _extract_forms(entry)
    conjugations = _extract_conjugations(forms)

    gender = _extract_gender_from_senses(entry, language_code)
    if gender is None and pos:
        gender = _extract_gender_from_pos(pos, language_code)

    return GrammaticalInfo(
        pos=pos,
        phonetics=phonetics,
        conjugations=conjugations,
        gender=gender,
    )


# ── Gender extraction ────────────────────────────────────────


def _extract_gender_from_pos(pos: str, language_code: str) -> str | None:
    """Extract grammatical gender from part of speech string."""
    if not pos:
        return None
    pos_lower = pos.lower()
    for keyword, article in GENDER_MAP.get(language_code, {}).items():
        if keyword in pos_lower:
            return article
    return None


def _extract_gender_from_senses(entry: dict[str, Any], language_code: str) -> str | None:
    """Extract grammatical gender from senses tags."""
    senses = entry.get("senses", [])
    if not senses:
        return None

    tags = senses[0].get("tags", [])
    if not tags:
        return None

    gender_map = GENDER_MAP.get(language_code, {})
    for tag in tags:
        article = gender_map.get(tag.lower())
        if article:
            return article
    return None


# ── Phonetics extraction ─────────────────────────────────────


def _extract_phonetics(entry: dict[str, Any]) -> str | None:
    """Extract IPA pronunciation from entry."""
    pronunciations = entry.get("pronunciations", [])
    for pron in pronunciations:
        if pron.get("type") == "ipa":
            return pron.get("text")
    return None


# ── Form extraction ──────────────────────────────────────────

# Tags to skip during form extraction
_SKIP_TAGS = {"table-tags", "inflection-template", "class", "multiword-construction"}

# Required tags for verb form extraction
_PRESENT_TAGS = {"present", "singular", "third-person"}
_PRETERITE_TAGS = {"preterite", "singular", "third-person"}
_PARTICIPLE_TAGS = {"participle", "past"}


def _is_valid_form(form: dict[str, Any]) -> tuple[str | None, set[str]]:
    """Check if form is valid and return word and tags."""
    word = form.get("word")
    tags = set(form.get("tags", []))

    if not word or not tags:
        return None, set()

    if tags & _SKIP_TAGS:
        return None, set()

    return word, tags


def _extract_verb_form(
    word: str,
    tags: set[str],
    result: dict[str, str],
    auxiliaries: list[str],
) -> None:
    """Extract verb conjugation form and update result in place."""
    if "auxiliary" in tags and word in ("haben", "sein"):
        if word not in auxiliaries:
            auxiliaries.append(word)
        return

    if _PRESENT_TAGS <= tags and "present" not in result:
        result["present"] = word
        return

    if "past" not in result:
        is_simple_past = tags == {"past"}
        is_preterite = _PRETERITE_TAGS <= tags and "subjunctive" not in tags
        if is_simple_past or is_preterite:
            result["past"] = word
            return

    if _PARTICIPLE_TAGS <= tags and "participle" not in result:
        result["participle"] = word


def _extract_noun_form(word: str, tags: set[str], result: dict[str, str]) -> None:
    """Extract noun declension form and update result in place."""
    for form_name in ("genitive", "plural", "feminine"):
        if form_name in tags and form_name not in result:
            result[form_name] = word
            return


def _extract_forms(entry: dict[str, Any]) -> dict[str, str] | None:
    """Extract grammatical forms from entry."""
    forms = entry.get("forms", [])
    if not forms:
        return None

    pos = entry.get("partOfSpeech", "").lower()
    is_verb = "verb" in pos

    result: dict[str, str] = {}
    auxiliaries: list[str] = []

    for form in forms:
        word, tags = _is_valid_form(form)
        if not word:
            continue

        if is_verb:
            _extract_verb_form(word, tags, result, auxiliaries)
        else:
            _extract_noun_form(word, tags, result)

    if auxiliaries:
        result["auxiliary"] = " / ".join(auxiliaries)

    return result if result else None


def _extract_conjugations(forms: dict[str, str] | None) -> dict[str, str] | None:
    """Filter relevant conjugation/declension forms from raw forms dict."""
    if not forms:
        return None
    conjugations: dict[str, str] = {}
    for key in ("present", "past", "participle", "auxiliary", "genitive", "plural"):
        if forms.get(key):
            conjugations[key] = forms[key]
    return conjugations or None


# ── Entry reading utilities ─────────────────────────────────
# These functions read from the entries/senses/subsenses structure
# returned by fetch().  They contain no business logic — only
# structure traversal and serialization.


def _format_sense_listing(entries: list[dict[str, Any]]) -> str:
    """Serialize entries/senses/subsenses into a numbered listing.

    Produces an X.Y / X.Y.Z indexed listing.  Does NOT include any
    prompt instructions — that is the caller's responsibility.
    """
    lines: list[str] = []
    for i, entry in enumerate(entries):
        pos = entry.get("partOfSpeech", "unknown")
        lines.append(f"entries[{i}] ({pos}):")
        for j, sense in enumerate(entry.get("senses", [])):
            lines.append(f"  {i}.{j} {sense.get('definition', '')}")
            for k, sub in enumerate(sense.get("subsenses", [])):
                lines.append(f"    {i}.{j}.{k} {sub.get('definition', '')}")
    return "\n".join(lines)


def _is_trivial(entries: list[dict[str, Any]]) -> bool:
    """Check if entries have a single sense with no subsenses.

    When trivial, sense selection can skip the LLM call entirely.
    """
    if len(entries) != 1:
        return False
    senses = entries[0].get("senses", [])
    if len(senses) > 1:
        return False
    if senses and senses[0].get("subsenses"):
        return False
    return True


def _clamp_index(entries: list[dict[str, Any]], index: _SenseIndex) -> _SenseIndex:
    """Clamp a SenseIndex to valid ranges within entries."""
    ei = max(0, min(index.entry, len(entries) - 1))
    senses = entries[ei].get("senses", [])
    si = max(0, min(index.sense, len(senses) - 1)) if senses else 0

    ssi = -1
    if index.subsense >= 0 and senses:
        subsenses = senses[si].get("subsenses", [])
        ssi = max(0, min(index.subsense, len(subsenses) - 1)) if subsenses else -1

    return _SenseIndex(entry=ei, sense=si, subsense=ssi)


def _read_definition(
    entry: dict[str, Any],
    sense_idx: int,
    subsense_idx: int,
) -> tuple[str, dict[str, Any] | None]:
    """Read definition string from selected entry/sense/subsense indices.

    Returns:
        Tuple of (definition_string, selected_sense_dict_or_None).
    """
    senses = entry.get("senses", [])
    if sense_idx >= len(senses):
        return "", None

    sense = senses[sense_idx]
    subsenses = sense.get("subsenses", [])
    if 0 <= subsense_idx < len(subsenses):
        subsense = subsenses[subsense_idx]
        return subsense.get("definition", ""), subsense
    return sense.get("definition", ""), sense


def _read_examples(
    sense: dict[str, Any],
    max_count: int = 3,
) -> list[str] | None:
    """Read examples from a single sense dict.

    Handles both string examples and dict examples with 'text' key.
    """
    examples: list[str] = []
    for example in sense.get("examples", [])[:max_count]:
        if isinstance(example, str):
            examples.append(example)
        elif isinstance(example, dict) and "text" in example:
            examples.append(example["text"])
    return examples if examples else None
