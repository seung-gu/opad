"""Free Dictionary API adapter.

Implements DictionaryPort by fetching entries from the Free Dictionary API.
Also provides entry parsing utilities (metadata, phonetics, forms, gender).

API Documentation: https://freedictionaryapi.com
Supported languages: German (de), English (en), French (fr), Spanish (es)
"""

import logging
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
    get_language_code,
)

logger = logging.getLogger(__name__)

FREE_DICTIONARY_API_BASE_URL = "https://freedictionaryapi.com/api/v1/entries"
API_TIMEOUT_SECONDS = 5.0


# ── Adapter ──────────────────────────────────────────────────


class FreeDictionaryAdapter:
    """Adapter that fetches dictionary entries from the Free Dictionary API."""

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

        except httpx.TimeoutException:
            logger.warning(
                "Free Dictionary API timeout after retries",
                extra={"word": word, "language": language},
            )
            return None
        except httpx.ConnectError:
            logger.warning(
                "Free Dictionary API connection error after retries",
                extra={"word": word, "language": language},
            )
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(
                "Free Dictionary API HTTP error",
                extra={"word": word, "language": language, "status_code": e.response.status_code},
            )
            return None
        except httpx.RequestError as e:
            logger.warning(
                "Free Dictionary API request error",
                extra={"word": word, "language": language, "error": str(e)},
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


def extract_entry_metadata(entry: dict[str, Any], language_code: str) -> dict[str, Any]:
    """Extract metadata from a single dictionary entry.

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
