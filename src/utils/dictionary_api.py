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
    """
    definition: str | None = None
    pos: str | None = None
    phonetics: str | None = None
    forms: dict[str, str] | None = None
    gender: str | None = None
    examples: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "definition": self.definition,
            "pos": self.pos,
            "phonetics": self.phonetics,
            "forms": self.forms,
            "gender": self.gender,
            "examples": self.examples,
        }


def _get_language_code(language: str) -> str | None:
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
    if not pos or language_code != "de":
        return None

    pos_lower = pos.lower()

    # German gender mapping
    if "masculine" in pos_lower or "männlich" in pos_lower:
        return "der"
    elif "feminine" in pos_lower or "weiblich" in pos_lower:
        return "die"
    elif "neuter" in pos_lower or "sächlich" in pos_lower:
        return "das"

    return None


def _extract_gender_from_senses(entry: dict[str, Any], language_code: str) -> str | None:
    """Extract grammatical gender from senses tags.

    Args:
        entry: Dictionary entry from API response.
        language_code: ISO 639-1 language code.

    Returns:
        Gender article (e.g., "der", "die", "das") or None.
    """
    if language_code != "de":
        return None

    senses = entry.get("senses", [])
    if not senses:
        return None

    tags = senses[0].get("tags", [])
    for tag in tags:
        tag_lower = tag.lower()
        if tag_lower == "masculine":
            return "der"
        elif tag_lower == "feminine":
            return "die"
        elif tag_lower == "neuter":
            return "das"

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


def _extract_definition(entry: dict[str, Any]) -> str | None:
    """Extract first definition from entry senses.

    Args:
        entry: Dictionary entry from API response.

    Returns:
        Definition string or None if not found.
    """
    senses = entry.get("senses", [])
    if not senses:
        return None

    first_sense = senses[0]
    return first_sense.get("definition")


def _extract_examples(entry: dict[str, Any], max_examples: int = 3) -> list[str] | None:
    """Extract example sentences from entry senses.

    Args:
        entry: Dictionary entry from API response.
        max_examples: Maximum number of examples to return.

    Returns:
        List of example sentences or None if not found.
    """
    senses = entry.get("senses", [])
    if not senses:
        return None

    examples: list[str] = []
    for sense in senses:
        sense_examples = sense.get("examples", [])
        for example in sense_examples:
            # Examples can be strings or dicts with 'text' key
            if isinstance(example, str):
                examples.append(example)
            elif isinstance(example, dict) and "text" in example:
                examples.append(example["text"])

            if len(examples) >= max_examples:
                break
        if len(examples) >= max_examples:
            break

    return examples if examples else None


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

    # Determine if this is a verb based on partOfSpeech
    pos = entry.get("partOfSpeech", "").lower()
    is_verb = "verb" in pos

    result: dict[str, str] = {}
    auxiliaries: list[str] = []

    for form in forms:
        word = form.get("word")
        tags = set(form.get("tags", []))

        if not word or not tags:
            continue

        # Skip metadata tags
        if tags & {"table-tags", "inflection-template", "class"}:
            continue

        # Skip multiword constructions (compound tenses like "habe gefahren")
        if "multiword-construction" in tags:
            continue

        # === Verb-specific extractions ===
        if is_verb:
            # Extract auxiliary verbs (haben/sein)
            if "auxiliary" in tags and word in ("haben", "sein"):
                if word not in auxiliaries:
                    auxiliaries.append(word)
                continue

            # Extract present 3rd person singular
            if ({"present", "singular", "third-person"} <= tags
                    and "present" not in result):
                result["present"] = word
                continue

            # Extract past/preterite 3rd person singular
            if "past" not in result:
                # Simple past tag
                if tags == {"past"}:
                    result["past"] = word
                    continue
                # Or preterite with 3rd person singular
                if ({"preterite", "singular", "third-person"} <= tags
                        and "subjunctive" not in tags):
                    result["past"] = word
                    continue

            # Extract past participle
            if ({"participle", "past"} <= tags
                    and "participle" not in result):
                result["participle"] = word

        # === Noun-specific extractions ===
        else:
            if "genitive" in tags and "genitive" not in result:
                result["genitive"] = word
            elif "plural" in tags and "plural" not in result:
                result["plural"] = word
            elif "feminine" in tags and "feminine" not in result:
                result["feminine"] = word

    # Add auxiliary if found (for verbs)
    if auxiliaries:
        result["auxiliary"] = " / ".join(auxiliaries)

    return result if result else None


def _parse_api_response(data: list[dict[str, Any]], language_code: str) -> DictionaryAPIResult:
    """Parse Free Dictionary API response into structured result.

    Args:
        data: Raw API response data.
        language_code: ISO 639-1 language code.

    Returns:
        Parsed DictionaryAPIResult.
    """
    result = DictionaryAPIResult()

    if not data:
        return result

    # API response is a dict: {"word": "...", "entries": [...]}
    entries = data.get("entries", [])

    if not entries:
        return result

    # Get first entry details
    entry = entries[0]

    # Extract part of speech
    result.pos = entry.get("partOfSpeech")

    # Extract pronunciation, definition, forms, and examples using helper functions
    result.phonetics = _extract_phonetics(entry)
    result.definition = _extract_definition(entry)
    result.forms = _extract_forms(entry)
    result.examples = _extract_examples(entry)

    # Extract gender from senses tags (for German nouns)
    result.gender = _extract_gender_from_senses(entry, language_code)
    # Fallback to POS-based extraction if senses didn't have gender
    if result.gender is None and result.pos:
        result.gender = _extract_gender_from_pos(result.pos, language_code)

    return result


def _strip_reflexive_pronoun(word: str, language_code: str) -> str:
    """Strip reflexive pronouns from verb lemmas for API lookup.

    German reflexive verbs (e.g., "sich gewöhnen") need the pronoun removed
    for dictionary API lookup. The API returns reflexive info in the response.

    Args:
        word: The word/lemma to process.
        language_code: ISO 639-1 language code.

    Returns:
        Word without reflexive pronoun prefix.
    """
    if language_code == "de":
        # German reflexive pronouns that might prefix lemmas
        reflexive_pronouns = ["sich ", "mich ", "dich ", "uns ", "euch "]
        word_lower = word.lower()
        for pronoun in reflexive_pronouns:
            if word_lower.startswith(pronoun):
                return word[len(pronoun):]
    return word


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
    language_code = _get_language_code(language)

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
            response = await client.get(url)

            if response.status_code == 404:
                logger.debug(
                    "Word not found in Free Dictionary API",
                    extra={"word": word, "language": language}
                )
                return None

            response.raise_for_status()
            data = response.json()

            result = _parse_api_response(data, language_code)

            logger.debug(
                "Free Dictionary API lookup successful",
                extra={
                    "word": word,
                    "language": language,
                    "has_definition": result.definition is not None,
                    "has_phonetics": result.phonetics is not None,
                    "has_forms": result.forms is not None,
                }
            )

            return result

    except httpx.TimeoutException:
        logger.warning(
            "Free Dictionary API timeout",
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
