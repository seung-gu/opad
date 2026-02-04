"""Tests for Free Dictionary API integration module.

Tests cover language code mapping, API response parsing, and async API calls
with proper error handling and edge cases.
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

from ..dictionary_api import (
    DictionaryAPIResult,
    _get_language_code,
    _extract_gender_from_pos,
    _extract_gender_from_senses,
    _extract_phonetics,
    _extract_definition,
    _extract_forms,
    _strip_reflexive_pronoun,
    _parse_api_response,
    fetch_from_free_dictionary_api,
    LANGUAGE_CODE_MAP,
)


class TestGetLanguageCode(unittest.TestCase):
    """Test language code conversion."""

    def test_supported_german(self):
        """Test German language code."""
        self.assertEqual(_get_language_code("German"), "de")

    def test_supported_english(self):
        """Test English language code."""
        self.assertEqual(_get_language_code("English"), "en")

    def test_supported_french(self):
        """Test French language code."""
        self.assertEqual(_get_language_code("French"), "fr")

    def test_supported_spanish(self):
        """Test Spanish language code."""
        self.assertEqual(_get_language_code("Spanish"), "es")

    def test_supported_italian(self):
        """Test Italian language code."""
        self.assertEqual(_get_language_code("Italian"), "it")

    def test_supported_portuguese(self):
        """Test Portuguese language code."""
        self.assertEqual(_get_language_code("Portuguese"), "pt")

    def test_supported_dutch(self):
        """Test Dutch language code."""
        self.assertEqual(_get_language_code("Dutch"), "nl")

    def test_supported_polish(self):
        """Test Polish language code."""
        self.assertEqual(_get_language_code("Polish"), "pl")

    def test_supported_russian(self):
        """Test Russian language code."""
        self.assertEqual(_get_language_code("Russian"), "ru")

    def test_unsupported_language(self):
        """Test unsupported language returns None."""
        self.assertIsNone(_get_language_code("Japanese"))

    def test_case_sensitive(self):
        """Test that language names are case-sensitive."""
        self.assertIsNone(_get_language_code("german"))
        self.assertIsNone(_get_language_code("GERMAN"))

    def test_empty_string(self):
        """Test empty string returns None."""
        self.assertIsNone(_get_language_code(""))

    def test_none_value(self):
        """Test None value returns None."""
        self.assertIsNone(_get_language_code(None))

    def test_all_supported_languages(self):
        """Test all languages in the LANGUAGE_CODE_MAP."""
        for language, code in LANGUAGE_CODE_MAP.items():
            self.assertEqual(_get_language_code(language), code)


class TestStripReflexivePronoun(unittest.TestCase):
    """Test reflexive pronoun stripping for API lookup."""

    def test_strip_sich_german(self):
        """Test stripping 'sich' from German reflexive verbs."""
        self.assertEqual(_strip_reflexive_pronoun("sich gewöhnen", "de"), "gewöhnen")

    def test_strip_sich_case_insensitive(self):
        """Test case-insensitive stripping."""
        self.assertEqual(_strip_reflexive_pronoun("Sich freuen", "de"), "freuen")

    def test_no_reflexive_unchanged(self):
        """Test non-reflexive verbs remain unchanged."""
        self.assertEqual(_strip_reflexive_pronoun("gehen", "de"), "gehen")

    def test_non_german_unchanged(self):
        """Test non-German languages don't strip."""
        self.assertEqual(_strip_reflexive_pronoun("sich test", "en"), "sich test")

    def test_other_pronouns(self):
        """Test other reflexive pronouns are stripped."""
        self.assertEqual(_strip_reflexive_pronoun("mich erinnern", "de"), "erinnern")
        self.assertEqual(_strip_reflexive_pronoun("dich setzen", "de"), "setzen")


class TestExtractGenderFromPos(unittest.TestCase):
    """Test grammatical gender extraction from part of speech."""

    def test_masculine_noun_german(self):
        """Test masculine noun returns 'der'."""
        self.assertEqual(
            _extract_gender_from_pos("masculine noun", "de"),
            "der"
        )

    def test_feminine_noun_german(self):
        """Test feminine noun returns 'die'."""
        self.assertEqual(
            _extract_gender_from_pos("feminine noun", "de"),
            "die"
        )

    def test_neuter_noun_german(self):
        """Test neuter noun returns 'das'."""
        self.assertEqual(
            _extract_gender_from_pos("neuter noun", "de"),
            "das"
        )

    def test_german_label_masculine(self):
        """Test German label for masculine (männlich)."""
        self.assertEqual(
            _extract_gender_from_pos("männlich noun", "de"),
            "der"
        )

    def test_german_label_feminine(self):
        """Test German label for feminine (weiblich)."""
        self.assertEqual(
            _extract_gender_from_pos("weiblich noun", "de"),
            "die"
        )

    def test_german_label_neuter(self):
        """Test German label for neuter (sächlich)."""
        self.assertEqual(
            _extract_gender_from_pos("sächlich noun", "de"),
            "das"
        )

    def test_case_insensitive(self):
        """Test gender extraction is case-insensitive."""
        self.assertEqual(
            _extract_gender_from_pos("MASCULINE NOUN", "de"),
            "der"
        )
        self.assertEqual(
            _extract_gender_from_pos("Feminine Noun", "de"),
            "die"
        )

    def test_non_gendered_language_returns_none(self):
        """Test languages without gender support return None."""
        self.assertIsNone(_extract_gender_from_pos("masculine noun", "en"))
        self.assertIsNone(_extract_gender_from_pos("masculine noun", "ja"))

    def test_french_gender_extraction(self):
        """Test French gender extraction from POS."""
        self.assertEqual(_extract_gender_from_pos("masculine noun", "fr"), "le")
        self.assertEqual(_extract_gender_from_pos("feminine noun", "fr"), "la")

    def test_spanish_gender_extraction(self):
        """Test Spanish gender extraction from POS."""
        self.assertEqual(_extract_gender_from_pos("masculine noun", "es"), "el")
        self.assertEqual(_extract_gender_from_pos("feminine noun", "es"), "la")

    def test_non_noun_german_returns_none(self):
        """Test non-noun parts of speech return None."""
        self.assertIsNone(_extract_gender_from_pos("verb", "de"))
        self.assertIsNone(_extract_gender_from_pos("adjective", "de"))
        self.assertIsNone(_extract_gender_from_pos("adverb", "de"))

    def test_empty_pos_returns_none(self):
        """Test empty part of speech returns None."""
        self.assertIsNone(_extract_gender_from_pos("", "de"))

    def test_none_pos_returns_none(self):
        """Test None part of speech returns None."""
        self.assertIsNone(_extract_gender_from_pos(None, "de"))

    def test_no_gender_indicator_returns_none(self):
        """Test part of speech without gender indicator returns None."""
        self.assertIsNone(_extract_gender_from_pos("noun", "de"))
        self.assertIsNone(_extract_gender_from_pos("regular noun", "de"))


class TestExtractGenderFromSenses(unittest.TestCase):
    """Test grammatical gender extraction from senses tags."""

    def test_masculine_tag_german(self):
        """Test masculine tag returns 'der'."""
        entry = {
            "senses": [
                {"definition": "dog", "tags": ["masculine"]}
            ]
        }
        self.assertEqual(_extract_gender_from_senses(entry, "de"), "der")

    def test_feminine_tag_german(self):
        """Test feminine tag returns 'die'."""
        entry = {
            "senses": [
                {"definition": "cat", "tags": ["feminine"]}
            ]
        }
        self.assertEqual(_extract_gender_from_senses(entry, "de"), "die")

    def test_neuter_tag_german(self):
        """Test neuter tag returns 'das'."""
        entry = {
            "senses": [
                {"definition": "child", "tags": ["neuter"]}
            ]
        }
        self.assertEqual(_extract_gender_from_senses(entry, "de"), "das")

    def test_case_insensitive(self):
        """Test gender extraction is case-insensitive."""
        entry = {
            "senses": [
                {"definition": "test", "tags": ["MASCULINE"]}
            ]
        }
        self.assertEqual(_extract_gender_from_senses(entry, "de"), "der")

    def test_non_gendered_language_returns_none(self):
        """Test languages without gender support return None."""
        entry = {
            "senses": [
                {"definition": "test", "tags": ["masculine"]}
            ]
        }
        self.assertIsNone(_extract_gender_from_senses(entry, "en"))
        self.assertIsNone(_extract_gender_from_senses(entry, "ja"))

    def test_french_gender_from_senses(self):
        """Test French gender extraction from senses tags."""
        entry = {
            "senses": [
                {"definition": "test", "tags": ["masculine"]}
            ]
        }
        self.assertEqual(_extract_gender_from_senses(entry, "fr"), "le")
        entry["senses"][0]["tags"] = ["feminine"]
        self.assertEqual(_extract_gender_from_senses(entry, "fr"), "la")

    def test_spanish_gender_from_senses(self):
        """Test Spanish gender extraction from senses tags."""
        entry = {
            "senses": [
                {"definition": "test", "tags": ["masculine"]}
            ]
        }
        self.assertEqual(_extract_gender_from_senses(entry, "es"), "el")
        entry["senses"][0]["tags"] = ["feminine"]
        self.assertEqual(_extract_gender_from_senses(entry, "es"), "la")

    def test_no_senses_returns_none(self):
        """Test entry with no senses returns None."""
        entry = {"senses": []}
        self.assertIsNone(_extract_gender_from_senses(entry, "de"))

    def test_no_tags_returns_none(self):
        """Test sense without tags returns None."""
        entry = {
            "senses": [
                {"definition": "test"}
            ]
        }
        self.assertIsNone(_extract_gender_from_senses(entry, "de"))

    def test_no_gender_tag_returns_none(self):
        """Test sense with non-gender tags returns None."""
        entry = {
            "senses": [
                {"definition": "test", "tags": ["verb", "transitive"]}
            ]
        }
        self.assertIsNone(_extract_gender_from_senses(entry, "de"))


class TestExtractPhonetics(unittest.TestCase):
    """Test IPA pronunciation extraction."""

    def test_extract_ipa_phonetics(self):
        """Test extracting IPA phonetics."""
        entry = {
            "pronunciations": [
                {"type": "ipa", "text": "/hʊnt/"}
            ]
        }
        self.assertEqual(_extract_phonetics(entry), "/hʊnt/")

    def test_multiple_pronunciations_returns_first_ipa(self):
        """Test that first IPA pronunciation is returned."""
        entry = {
            "pronunciations": [
                {"type": "phonetic", "text": "hoont"},
                {"type": "ipa", "text": "/hʊnt/"},
                {"type": "ipa", "text": "/huːnt/"}
            ]
        }
        self.assertEqual(_extract_phonetics(entry), "/hʊnt/")

    def test_non_ipa_pronunciations_skipped(self):
        """Test that non-IPA pronunciations are skipped."""
        entry = {
            "pronunciations": [
                {"type": "phonetic", "text": "hoont"},
                {"type": "written", "text": "hunt"}
            ]
        }
        self.assertIsNone(_extract_phonetics(entry))

    def test_no_pronunciations(self):
        """Test entry with no pronunciations returns None."""
        entry = {"pronunciations": []}
        self.assertIsNone(_extract_phonetics(entry))

    def test_missing_pronunciations_key(self):
        """Test entry without pronunciations key returns None."""
        entry = {}
        self.assertIsNone(_extract_phonetics(entry))

    def test_phonetics_with_empty_text(self):
        """Test IPA entry with empty text returns empty string."""
        entry = {
            "pronunciations": [
                {"type": "ipa", "text": ""}
            ]
        }
        self.assertEqual(_extract_phonetics(entry), "")

    def test_phonetics_missing_text_key(self):
        """Test pronunciation without text key returns None."""
        entry = {
            "pronunciations": [
                {"type": "ipa"}
            ]
        }
        self.assertIsNone(_extract_phonetics(entry))


class TestExtractDefinition(unittest.TestCase):
    """Test definition extraction from API response.

    Note: Free Dictionary API uses 'senses' with direct 'definition' field,
    not 'meanings' with nested 'definitions' array.
    """

    def test_extract_first_definition(self):
        """Test extracting first definition from senses."""
        entry = {
            "senses": [
                {"definition": "A domesticated carnivorous mammal"}
            ]
        }
        result = _extract_definition(entry)
        self.assertEqual(result, "A domesticated carnivorous mammal")

    def test_multiple_senses_returns_first(self):
        """Test that first sense's definition is returned."""
        entry = {
            "senses": [
                {"definition": "First definition"},
                {"definition": "Second definition"}
            ]
        }
        result = _extract_definition(entry)
        self.assertEqual(result, "First definition")

    def test_no_senses(self):
        """Test entry with no senses returns None."""
        entry = {"senses": []}
        self.assertIsNone(_extract_definition(entry))

    def test_missing_senses_key(self):
        """Test entry without senses key returns None."""
        entry = {}
        self.assertIsNone(_extract_definition(entry))

    def test_sense_missing_definition_key(self):
        """Test sense without definition key returns None."""
        entry = {
            "senses": [
                {"examples": ["Example text"]}
            ]
        }
        self.assertIsNone(_extract_definition(entry))

    def test_sense_with_tags_and_definition(self):
        """Test sense with both tags and definition."""
        entry = {
            "senses": [
                {"definition": "dog, hound", "tags": ["masculine"]}
            ]
        }
        result = _extract_definition(entry)
        self.assertEqual(result, "dog, hound")


class TestExtractForms(unittest.TestCase):
    """Test grammatical forms extraction.

    Forms extraction is POS-aware:
    - Verbs: extracts present, past, participle, auxiliary
    - Nouns: extracts genitive, plural, feminine
    """

    # === Noun form tests ===
    def test_noun_extract_genitive_plural(self):
        """Test extracting noun forms (genitive, plural)."""
        entry = {
            "partOfSpeech": "noun",
            "forms": [
                {"word": "Hundes", "tags": ["genitive"]},
                {"word": "Hunde", "tags": ["plural"]},
                {"word": "Hündin", "tags": ["feminine"]}
            ]
        }
        result = _extract_forms(entry)
        self.assertEqual(result, {
            "genitive": "Hundes",
            "plural": "Hunde",
            "feminine": "Hündin"
        })

    def test_noun_single_form(self):
        """Test extracting single noun form."""
        entry = {
            "partOfSpeech": "noun",
            "forms": [
                {"word": "Katzen", "tags": ["plural"]}
            ]
        }
        result = _extract_forms(entry)
        self.assertEqual(result, {"plural": "Katzen"})

    # === Verb form tests ===
    def test_verb_extract_conjugations(self):
        """Test extracting verb conjugation forms."""
        entry = {
            "partOfSpeech": "verb",
            "forms": [
                {"word": "fährt", "tags": ["present", "singular", "third-person"]},
                {"word": "fuhr", "tags": ["past"]},
                {"word": "gefahren", "tags": ["participle", "past"]},
                {"word": "haben", "tags": ["auxiliary"]},
                {"word": "sein", "tags": ["auxiliary"]}
            ]
        }
        result = _extract_forms(entry)
        self.assertEqual(result, {
            "present": "fährt",
            "past": "fuhr",
            "participle": "gefahren",
            "auxiliary": "haben / sein"
        })

    def test_verb_preterite_form(self):
        """Test extracting preterite as past form."""
        entry = {
            "partOfSpeech": "verb",
            "forms": [
                {"word": "ging", "tags": ["preterite", "singular", "third-person", "indicative"]}
            ]
        }
        result = _extract_forms(entry)
        self.assertEqual(result, {"past": "ging"})

    def test_verb_single_auxiliary(self):
        """Test verb with single auxiliary."""
        entry = {
            "partOfSpeech": "verb",
            "forms": [
                {"word": "sein", "tags": ["auxiliary"]},
                {"word": "geht", "tags": ["present", "singular", "third-person"]}
            ]
        }
        result = _extract_forms(entry)
        self.assertEqual(result["auxiliary"], "sein")
        self.assertEqual(result["present"], "geht")

    def test_verb_skips_multiword_constructions(self):
        """Test that multiword constructions are skipped."""
        entry = {
            "partOfSpeech": "verb",
            "forms": [
                {"word": "habe gefahren", "tags": ["multiword-construction", "perfect"]},
                {"word": "fährt", "tags": ["present", "singular", "third-person"]}
            ]
        }
        result = _extract_forms(entry)
        self.assertEqual(result, {"present": "fährt"})

    def test_verb_skips_metadata_tags(self):
        """Test that metadata tags are skipped."""
        entry = {
            "partOfSpeech": "verb",
            "forms": [
                {"word": "strong", "tags": ["table-tags"]},
                {"word": "de-conj", "tags": ["inflection-template"]},
                {"word": "fährt", "tags": ["present", "singular", "third-person"]}
            ]
        }
        result = _extract_forms(entry)
        self.assertEqual(result, {"present": "fährt"})

    # === Edge case tests ===
    def test_no_forms(self):
        """Test entry with no forms returns None."""
        entry = {"partOfSpeech": "noun", "forms": []}
        self.assertIsNone(_extract_forms(entry))

    def test_missing_forms_key(self):
        """Test entry without forms key returns None."""
        entry = {"partOfSpeech": "noun"}
        self.assertIsNone(_extract_forms(entry))

    def test_form_missing_word_is_skipped(self):
        """Test form without word is skipped."""
        entry = {
            "partOfSpeech": "noun",
            "forms": [
                {"tags": ["genitive"]},
                {"word": "Hunde", "tags": ["plural"]}
            ]
        }
        result = _extract_forms(entry)
        self.assertEqual(result, {"plural": "Hunde"})

    def test_form_missing_tags_is_skipped(self):
        """Test form without tags is skipped."""
        entry = {
            "partOfSpeech": "noun",
            "forms": [
                {"word": "Hund"},
                {"word": "Hunde", "tags": ["plural"]}
            ]
        }
        result = _extract_forms(entry)
        self.assertEqual(result, {"plural": "Hunde"})

    def test_all_forms_invalid_returns_none(self):
        """Test that all invalid forms returns None."""
        entry = {
            "partOfSpeech": "noun",
            "forms": [
                {"word": "Hund"},
                {"tags": ["genitive"]}
            ]
        }
        self.assertIsNone(_extract_forms(entry))

    def test_unknown_pos_extracts_noun_forms(self):
        """Test that unknown POS extracts noun forms (default)."""
        entry = {
            "partOfSpeech": "adjective",
            "forms": [
                {"word": "schneller", "tags": ["plural"]}
            ]
        }
        result = _extract_forms(entry)
        self.assertEqual(result, {"plural": "schneller"})


class TestParseApiResponse(unittest.TestCase):
    """Test parsing complete API response.

    Note: Free Dictionary API uses 'senses' with direct 'definition' field
    and 'tags' for grammatical info like gender.
    """

    def test_parse_complete_response_german(self):
        """Test parsing complete German response with senses."""
        data = {
            "word": "Hund",
            "entries": [
                {
                    "partOfSpeech": "noun",
                    "pronunciations": [
                        {"type": "ipa", "text": "/hʊnt/"}
                    ],
                    "senses": [
                        {
                            "definition": "dog, hound",
                            "tags": ["masculine"]
                        }
                    ],
                    "forms": [
                        {"word": "Hundes", "tags": ["genitive"]},
                        {"word": "Hunde", "tags": ["plural"]}
                    ]
                }
            ]
        }
        result = _parse_api_response(data, "de")
        self.assertEqual(result.pos, "noun")
        self.assertEqual(result.gender, "der")
        self.assertEqual(result.phonetics, "/hʊnt/")
        self.assertEqual(result.definition, "dog, hound")
        self.assertEqual(result.forms, {"genitive": "Hundes", "plural": "Hunde"})

    def test_parse_response_without_gender(self):
        """Test parsing English response without gender."""
        data = {
            "word": "dog",
            "entries": [
                {
                    "partOfSpeech": "noun",
                    "pronunciations": [
                        {"type": "ipa", "text": "/dɒɡ/"}
                    ],
                    "senses": [
                        {"definition": "A domesticated carnivorous mammal"}
                    ]
                }
            ]
        }
        result = _parse_api_response(data, "en")
        self.assertEqual(result.pos, "noun")
        self.assertIsNone(result.gender)
        self.assertEqual(result.phonetics, "/dɒɡ/")

    def test_parse_verb_response_german(self):
        """Test parsing German verb with conjugation forms."""
        data = {
            "word": "fahren",
            "entries": [
                {
                    "partOfSpeech": "verb",
                    "pronunciations": [
                        {"type": "ipa", "text": "[ˈfaːʁən]"}
                    ],
                    "senses": [
                        {"definition": "to go, to drive"}
                    ],
                    "forms": [
                        {"word": "fährt", "tags": ["present", "singular", "third-person"]},
                        {"word": "fuhr", "tags": ["past"]},
                        {"word": "gefahren", "tags": ["participle", "past"]},
                        {"word": "haben", "tags": ["auxiliary"]},
                        {"word": "sein", "tags": ["auxiliary"]}
                    ]
                }
            ]
        }
        result = _parse_api_response(data, "de")
        self.assertEqual(result.pos, "verb")
        self.assertEqual(result.definition, "to go, to drive")
        self.assertEqual(result.phonetics, "[ˈfaːʁən]")
        self.assertEqual(result.forms, {
            "present": "fährt",
            "past": "fuhr",
            "participle": "gefahren",
            "auxiliary": "haben / sein"
        })

    def test_parse_partial_response(self):
        """Test parsing response with missing optional fields."""
        data = {
            "word": "test",
            "entries": [
                {
                    "partOfSpeech": "noun"
                }
            ]
        }
        result = _parse_api_response(data, "de")
        self.assertEqual(result.pos, "noun")
        self.assertIsNone(result.phonetics)
        self.assertIsNone(result.definition)
        self.assertIsNone(result.forms)

    def test_parse_empty_data(self):
        """Test parsing empty data returns empty result."""
        result = _parse_api_response({}, "de")
        self.assertIsNone(result.pos)
        self.assertIsNone(result.phonetics)
        self.assertIsNone(result.definition)
        self.assertIsNone(result.forms)
        self.assertIsNone(result.gender)

    def test_parse_no_entries(self):
        """Test parsing response without entries."""
        data = {"word": "test", "entries": []}
        result = _parse_api_response(data, "de")
        self.assertIsNone(result.pos)

    def test_parse_uses_first_entry(self):
        """Test that first entry is used."""
        data = {
            "word": "test",
            "entries": [
                {
                    "partOfSpeech": "first entry",
                    "senses": [{"definition": "First"}]
                },
                {
                    "partOfSpeech": "second entry",
                    "senses": [{"definition": "Second"}]
                }
            ]
        }
        result = _parse_api_response(data, "de")
        self.assertEqual(result.pos, "first entry")
        self.assertEqual(result.definition, "First")

    def test_result_to_dict(self):
        """Test DictionaryAPIResult.to_dict() method."""
        result = DictionaryAPIResult(
            definition="Test definition",
            pos="noun",
            phonetics="/test/",
            forms={"plural": "tests"},
            gender="der"
        )
        result_dict = result.to_dict()
        self.assertEqual(result_dict["definition"], "Test definition")
        self.assertEqual(result_dict["pos"], "noun")
        self.assertEqual(result_dict["phonetics"], "/test/")
        self.assertEqual(result_dict["forms"], {"plural": "tests"})
        self.assertEqual(result_dict["gender"], "der")

    def test_result_to_dict_with_none_values(self):
        """Test to_dict with None values."""
        result = DictionaryAPIResult()
        result_dict = result.to_dict()
        self.assertIsNone(result_dict["definition"])
        self.assertIsNone(result_dict["pos"])
        self.assertIsNone(result_dict["phonetics"])
        self.assertIsNone(result_dict["forms"])
        self.assertIsNone(result_dict["gender"])


class TestFetchFromFreePatternaryApi(unittest.IsolatedAsyncioTestCase):
    """Test async fetch from Free Dictionary API."""

    @patch('utils.dictionary_api.httpx.AsyncClient')
    async def test_successful_fetch_german(self, mock_client_class):
        """Test successful API fetch for German word."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "word": "Hund",
            "entries": [
                {
                    "partOfSpeech": "noun",
                    "pronunciations": [{"type": "ipa", "text": "/hʊnt/"}],
                    "senses": [
                        {"definition": "dog, hound", "tags": ["masculine"]}
                    ]
                }
            ]
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_client_class.return_value = mock_client

        result = await fetch_from_free_dictionary_api("Hund", "German")

        self.assertIsNotNone(result)
        self.assertEqual(result.definition, "dog, hound")
        self.assertEqual(result.phonetics, "/hʊnt/")
        self.assertEqual(result.pos, "noun")
        self.assertEqual(result.gender, "der")

    @patch('utils.dictionary_api.httpx.AsyncClient')
    async def test_unsupported_language(self, mock_client_class):
        """Test unsupported language returns None without API call."""
        result = await fetch_from_free_dictionary_api("word", "Japanese")
        self.assertIsNone(result)
        mock_client_class.assert_not_called()

    @patch('utils.dictionary_api.httpx.AsyncClient')
    async def test_404_not_found(self, mock_client_class):
        """Test 404 response returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_client_class.return_value = mock_client

        result = await fetch_from_free_dictionary_api("nonexistent", "German")

        self.assertIsNone(result)

    @patch('utils.dictionary_api.httpx.AsyncClient')
    async def test_timeout_exception(self, mock_client_class):
        """Test timeout exception returns None."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("Timeout")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_client_class.return_value = mock_client

        result = await fetch_from_free_dictionary_api("Hund", "German")

        self.assertIsNone(result)

    @patch('utils.dictionary_api.httpx.AsyncClient')
    async def test_http_status_error(self, mock_client_class):
        """Test HTTP status error returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=mock_response
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_client_class.return_value = mock_client

        result = await fetch_from_free_dictionary_api("Hund", "German")

        self.assertIsNone(result)

    @patch('utils.dictionary_api.httpx.AsyncClient')
    async def test_request_error(self, mock_client_class):
        """Test network request error returns None."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.RequestError("Connection failed")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_client_class.return_value = mock_client

        result = await fetch_from_free_dictionary_api("Hund", "German")

        self.assertIsNone(result)

    @patch('utils.dictionary_api.httpx.AsyncClient')
    async def test_json_decode_error(self, mock_client_class):
        """Test JSON decode error returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_client_class.return_value = mock_client

        result = await fetch_from_free_dictionary_api("Hund", "German")

        self.assertIsNone(result)

    @patch('utils.dictionary_api.httpx.AsyncClient')
    async def test_unexpected_exception(self, mock_client_class):
        """Test unexpected exception returns None."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = RuntimeError("Unexpected error")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_client_class.return_value = mock_client

        result = await fetch_from_free_dictionary_api("Hund", "German")

        self.assertIsNone(result)

    @patch('utils.dictionary_api.httpx.AsyncClient')
    async def test_api_url_construction(self, mock_client_class):
        """Test that URL is correctly constructed with word and language."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"entries": []}]

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_client_class.return_value = mock_client

        await fetch_from_free_dictionary_api("Hund", "German")

        # Verify URL contains language code and word
        called_url = mock_client.get.call_args[0][0]
        self.assertIn("/de/", called_url)
        self.assertIn("Hund", called_url)

    @patch('utils.dictionary_api.httpx.AsyncClient')
    async def test_url_encoding_special_characters(self, mock_client_class):
        """Test that special characters are properly URL-encoded."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"entries": []}]

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_client_class.return_value = mock_client

        await fetch_from_free_dictionary_api("über", "German")

        called_url = mock_client.get.call_args[0][0]
        # Umlaut should be URL-encoded
        self.assertIn("%C3%BCber", called_url)

    @patch('utils.dictionary_api.httpx.AsyncClient')
    async def test_all_supported_languages(self, mock_client_class):
        """Test fetch works with all supported languages."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"word": "test", "entries": [{"senses": []}]}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_client_class.return_value = mock_client

        languages = ["German", "English", "French", "Spanish", "Italian",
                     "Portuguese", "Dutch", "Polish", "Russian"]

        for language in languages:
            result = await fetch_from_free_dictionary_api("test", language)
            self.assertIsNotNone(result)

    @patch('utils.dictionary_api.httpx.AsyncClient')
    async def test_empty_response_data(self, mock_client_class):
        """Test handling of empty response data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_client_class.return_value = mock_client

        result = await fetch_from_free_dictionary_api("Hund", "German")

        # Should return DictionaryAPIResult with all None values
        self.assertIsNotNone(result)
        self.assertIsNone(result.definition)
        self.assertIsNone(result.pos)


# Pytest-style tests for convenience
@pytest.mark.asyncio
async def test_fetch_successful_with_pytest():
    """Pytest version of successful fetch test."""
    with patch('utils.dictionary_api.httpx.AsyncClient') as mock_client_class:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "word": "test",
            "entries": [
                {
                    "partOfSpeech": "noun",
                    "pronunciations": [{"type": "ipa", "text": "/test/"}],
                    "senses": [
                        {"definition": "Test definition"}
                    ]
                }
            ]
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_client_class.return_value = mock_client

        result = await fetch_from_free_dictionary_api("test", "English")

        assert result is not None
        assert result.definition == "Test definition"
        assert result.phonetics == "/test/"


if __name__ == '__main__':
    unittest.main()
