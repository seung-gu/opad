"""Free Dictionary API integration for pronunciation and word forms.

This module provides integration with the Free Dictionary API to fetch
pronunciation (IPA), grammatical forms, and definitions for words.
It's used as part of the hybrid dictionary lookup approach.

API Documentation: https://freedictionaryapi.com
Supported languages: German (de), English (en), French (fr), Spanish (es)
"""

import logging
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

from utils.language_metadata import (
    GENDER_MAP, REFLEXIVE_PREFIXES, REFLEXIVE_SUFFIXES, PHONETICS_SUPPORTED,
)

logger = logging.getLogger(__name__)

# Map full language names to ISO 639-1 codes
LANGUAGE_CODE_MAP: dict[str, str] = {
    "German": "de",
    "English": "en",
    "French": "fr",
    "Spanish": "es",
    "Italian": "it",
    "Portuguese": "pt",
    "Dutch": "nl",
    "Polish": "pl",
    "Russian": "ru",
}

FREE_DICTIONARY_API_BASE_URL = "https://freedictionaryapi.com/api/v1/entries"
API_TIMEOUT_SECONDS = 5.0


@dataclass
class DictionaryAPIResult:
    """Result from Free Dictionary API lookup.

    Attributes:
        definition: Word definition in target language.
        pos: Part of speech (noun, verb, adjective, etc.).
        phonetics: IPA pronunciation (e.g., "/hʊnt/").
        forms: Grammatical forms (e.g., genitive, plural).
        gender: Grammatical gender for nouns (e.g., "der", "die", "das").
        examples: Example sentences showing word usage.
        all_entries: All entries from API for context-aware selection.
    """
    definition: str | None = None
    pos: str | None = None
    phonetics: str | None = None
    forms: dict[str, str] | None = None
    gender: str | None = None
    examples: list[str] | None = None
    all_entries: list[dict] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "definition": self.definition,
            "pos": self.pos,
            "phonetics": self.phonetics,
            "forms": self.forms,
            "gender": self.gender,
            "examples": self.examples,
            "all_entries": self.all_entries,
        }


def get_language_code(language: str) -> str | None:
    """Convert full language name to ISO 639-1 code.

    Args:
        language: Full language name (e.g., "German", "English").

    Returns:
        ISO 639-1 code (e.g., "de", "en") or None if not supported.
    """
    return LANGUAGE_CODE_MAP.get(language)


def _extract_gender_from_pos(pos: str, language_code: str) -> str | None:
    """Extract grammatical gender from part of speech string.

    Args:
        pos: Part of speech string (e.g., "noun", "masculine noun").
        language_code: ISO 639-1 language code.

    Returns:
        Gender article (e.g., "der", "die", "das") or None.
    """
    if not pos:
        return None
    pos_lower = pos.lower()
    for keyword, article in GENDER_MAP.get(language_code, {}).items():
        if keyword in pos_lower:
            return article
    return None


def _extract_gender_from_senses(entry: dict[str, Any], language_code: str) -> str | None:
    """Extract grammatical gender from senses tags.

    Args:
        entry: Dictionary entry from API response.
        language_code: ISO 639-1 language code.

    Returns:
        Gender article (e.g., "der", "die", "das") or None.
    """
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


def _extract_phonetics(entry: dict[str, Any]) -> str | None:
    """Extract IPA pronunciation from entry.

    Args:
        entry: Dictionary entry from API response.

    Returns:
        IPA phonetics string or None if not found.
    """
    pronunciations = entry.get("pronunciations", [])
    for pron in pronunciations:
        if pron.get("type") == "ipa":
            return pron.get("text")
    return None


# Tags to skip during form extraction
_SKIP_TAGS = {"table-tags", "inflection-template", "class", "multiword-construction"}

# Required tags for verb form extraction
_PRESENT_TAGS = {"present", "singular", "third-person"}
_PRETERITE_TAGS = {"preterite", "singular", "third-person"}
_PARTICIPLE_TAGS = {"participle", "past"}


def _is_valid_form(form: dict[str, Any]) -> tuple[str | None, set[str]]:
    """Check if form is valid and return word and tags.

    Args:
        form: Form dict from API response.

    Returns:
        Tuple of (word, tags) if valid, (None, empty set) if invalid.
    """
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
    auxiliaries: list[str]
) -> None:
    """Extract verb conjugation form and update result in place.

    Args:
        word: The word form.
        tags: Set of grammatical tags.
        result: Result dict to update.
        auxiliaries: List of auxiliary verbs to update.
    """
    # Auxiliary verbs (haben/sein)
    if "auxiliary" in tags and word in ("haben", "sein"):
        if word not in auxiliaries:
            auxiliaries.append(word)
        return

    # Present 3rd person singular
    if _PRESENT_TAGS <= tags and "present" not in result:
        result["present"] = word
        return

    # Past/preterite 3rd person singular
    if "past" not in result:
        is_simple_past = tags == {"past"}
        is_preterite = _PRETERITE_TAGS <= tags and "subjunctive" not in tags
        if is_simple_past or is_preterite:
            result["past"] = word
            return

    # Past participle
    if _PARTICIPLE_TAGS <= tags and "participle" not in result:
        result["participle"] = word


def _extract_noun_form(word: str, tags: set[str], result: dict[str, str]) -> None:
    """Extract noun declension form and update result in place.

    Args:
        word: The word form.
        tags: Set of grammatical tags.
        result: Result dict to update.
    """
    # Check each noun form type
    for form_name in ("genitive", "plural", "feminine"):
        if form_name in tags and form_name not in result:
            result[form_name] = word
            return


def _extract_forms(entry: dict[str, Any]) -> dict[str, str] | None:
    """Extract grammatical forms from entry.

    For verbs, extracts key conjugation forms:
    - present: 3rd person singular present tense
    - past: 3rd person singular past/preterite
    - participle: past participle
    - auxiliary: haben/sein (for compound tenses)

    For nouns, extracts:
    - genitive, plural, feminine

    Args:
        entry: Dictionary entry from API response.

    Returns:
        Dictionary of form names to words, or None if no forms.
    """
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



def extract_entry_metadata(entry: dict[str, Any], language_code: str) -> dict[str, Any]:
    """Extract metadata from a single dictionary entry.

    Used by the service layer to get POS, phonetics, forms, and gender
    from a specific entry (not necessarily entries[0]).

    Args:
        entry: A single entry dict from API response.
        language_code: ISO 639-1 language code.

    Returns:
        Dict with keys: pos, phonetics, forms, gender, senses.
    """
    pos = entry.get("partOfSpeech")
    phonetics = _extract_phonetics(entry) if language_code in PHONETICS_SUPPORTED else None
    forms = _extract_forms(entry)
    senses = entry.get("senses", [])

    gender = _extract_gender_from_senses(entry, language_code)
    if gender is None and pos:
        gender = _extract_gender_from_pos(pos, language_code)

    return {
        "pos": pos,
        "phonetics": phonetics,
        "forms": forms,
        "gender": gender,
        "senses": senses,
    }


def _strip_reflexive_pronoun(word: str, language_code: str) -> str:
    """Strip reflexive pronouns from verb lemmas for API lookup.

    Args:
        word: The word/lemma to process.
        language_code: ISO 639-1 language code.

    Returns:
        Word without reflexive pronoun prefix.
    """
    word_lower = word.lower()
    for prefix in REFLEXIVE_PREFIXES.get(language_code, []):
        if word_lower.startswith(prefix):
            return word[len(prefix):]
    for suffix in REFLEXIVE_SUFFIXES.get(language_code, []):
        if word_lower.endswith(suffix):
            return word[:-2]
    return word


@retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    reraise=True
)
async def _fetch_with_retry(client: httpx.AsyncClient, url: str) -> httpx.Response:
    """Fetch URL with automatic retry on transient failures.

    Retries up to 3 times with exponential backoff (1s, 2s, 4s) on:
    - Timeout exceptions
    - Connection errors

    Args:
        client: HTTP client instance.
        url: URL to fetch.

    Returns:
        HTTP response.

    Raises:
        httpx.TimeoutException: After 3 timeout attempts.
        httpx.ConnectError: After 3 connection error attempts.
    """
    return await client.get(url)


async def fetch_from_free_dictionary_api(
    word: str,
    language: str
) -> DictionaryAPIResult | None:
    """Fetch word information from Free Dictionary API.

    This function queries the Free Dictionary API to get pronunciation,
    grammatical forms, and definitions for a word. It's designed to be
    used as part of a hybrid lookup approach where LLM provides lemma
    and level, while this API provides pronunciation and forms.

    Args:
        word: The word to look up.
        language: Full language name (e.g., "German", "English").

    Returns:
        DictionaryAPIResult with pronunciation, forms, etc., or None on error.
        Returns None if the language is not supported or API call fails.
    """
    language_code = get_language_code(language)

    if not language_code:
        logger.debug(
            "Language not supported by Free Dictionary API",
            extra={"language": language}
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
                    extra={"word": word, "language": language}
                )
                return None

            response.raise_for_status()
            data = response.json()

            # Validate response structure
            if not isinstance(data, dict):
                logger.warning(
                    "Unexpected response type from Free Dictionary API",
                    extra={"word": word, "language": language, "type": type(data).__name__}
                )
                return None

            entries = data.get("entries", [])
            if not entries:
                logger.debug(
                    "Free Dictionary API returned no entries",
                    extra={"word": word, "language": language}
                )
                return None

            result = DictionaryAPIResult(all_entries=entries)

            logger.debug(
                "Free Dictionary API lookup successful",
                extra={
                    "word": word,
                    "language": language,
                    "entry_count": len(entries),
                }
            )

            return result

    except httpx.TimeoutException:
        logger.warning(
            "Free Dictionary API timeout after retries",
            extra={"word": word, "language": language}
        )
        return None
    except httpx.ConnectError:
        logger.warning(
            "Free Dictionary API connection error after retries",
            extra={"word": word, "language": language}
        )
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(
            "Free Dictionary API HTTP error",
            extra={
                "word": word,
                "language": language,
                "status_code": e.response.status_code,
            }
        )
        return None
    except httpx.RequestError as e:
        logger.warning(
            "Free Dictionary API request error",
            extra={"word": word, "language": language, "error": str(e)}
        )
        return None
    except Exception as e:
        logger.error(
            "Unexpected error calling Free Dictionary API",
            extra={"word": word, "language": language, "error": str(e)},
            exc_info=True
        )
        return None
