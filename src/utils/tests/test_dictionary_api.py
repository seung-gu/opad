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
    get_language_code,
    _extract_gender_from_pos,
    _extract_gender_from_senses,
    _extract_phonetics,
    _extract_forms,
    _strip_reflexive_pronoun,
    extract_entry_metadata,
    fetch_from_free_dictionary_api,
    LANGUAGE_CODE_MAP,
)


class TestGetLanguageCode(unittest.TestCase):
    """Test language code conversion."""

    def test_supported_german(self):
        """Test German language code."""
        self.assertEqual(get_language_code("German"), "de")

    def test_supported_english(self):
        """Test English language code."""
        self.assertEqual(get_language_code("English"), "en")

    def test_supported_french(self):
        """Test French language code."""
        self.assertEqual(get_language_code("French"), "fr")

    def test_supported_spanish(self):
        """Test Spanish language code."""
        self.assertEqual(get_language_code("Spanish"), "es")

    def test_supported_italian(self):
        """Test Italian language code."""
        self.assertEqual(get_language_code("Italian"), "it")

    def test_supported_portuguese(self):
        """Test Portuguese language code."""
        self.assertEqual(get_language_code("Portuguese"), "pt")

    def test_supported_dutch(self):
        """Test Dutch language code."""
        self.assertEqual(get_language_code("Dutch"), "nl")

    def test_supported_polish(self):
        """Test Polish language code."""
        self.assertEqual(get_language_code("Polish"), "pl")

    def test_supported_russian(self):
        """Test Russian language code."""
        self.assertEqual(get_language_code("Russian"), "ru")

    def test_unsupported_language(self):
        """Test unsupported language returns None."""
        self.assertIsNone(get_language_code("Japanese"))

    def test_case_sensitive(self):
        """Test that language names are case-sensitive."""
        self.assertIsNone(get_language_code("german"))
        self.assertIsNone(get_language_code("GERMAN"))

    def test_empty_string(self):
        """Test empty string returns None."""
        self.assertIsNone(get_language_code(""))

    def test_none_value(self):
        """Test None value returns None."""
        self.assertIsNone(get_language_code(None))

    def test_all_supported_languages(self):
        """Test all languages in the LANGUAGE_CODE_MAP."""
        for language, code in LANGUAGE_CODE_MAP.items():
            self.assertEqual(get_language_code(language), code)


class TestStripReflexivePronoun(unittest.TestCase):
    """Test reflexive pronoun stripping for API lookup."""

    # German
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

    def test_german_uns_euch(self):
        """Test German uns/euch reflexive pronouns."""
        self.assertEqual(_strip_reflexive_pronoun("uns treffen", "de"), "treffen")
        self.assertEqual(_strip_reflexive_pronoun("euch beeilen", "de"), "beeilen")

    def test_german_non_reflexive_noun(self):
        """Test German non-reflexive words stay unchanged."""
        self.assertEqual(_strip_reflexive_pronoun("Haus", "de"), "Haus")

    # French
    def test_french_strip_se(self):
        """Test stripping 'se' from French reflexive verbs."""
        self.assertEqual(_strip_reflexive_pronoun("se lever", "fr"), "lever")
        self.assertEqual(_strip_reflexive_pronoun("Se coucher", "fr"), "coucher")

    def test_french_strip_s_apostrophe(self):
        """Test stripping s' from French reflexive verbs."""
        self.assertEqual(_strip_reflexive_pronoun("s'asseoir", "fr"), "asseoir")
        self.assertEqual(_strip_reflexive_pronoun("S'habiller", "fr"), "habiller")

    def test_french_no_reflexive(self):
        """Test French non-reflexive verbs stay unchanged."""
        self.assertEqual(_strip_reflexive_pronoun("manger", "fr"), "manger")

    # Spanish
    def test_spanish_strip_arse(self):
        """Test stripping -arse suffix from Spanish reflexive verbs."""
        self.assertEqual(_strip_reflexive_pronoun("levantarse", "es"), "levantar")
        self.assertEqual(_strip_reflexive_pronoun("bañarse", "es"), "bañar")

    def test_spanish_strip_erse(self):
        """Test stripping -erse suffix from Spanish reflexive verbs."""
        self.assertEqual(_strip_reflexive_pronoun("ponerse", "es"), "poner")
        self.assertEqual(_strip_reflexive_pronoun("moverse", "es"), "mover")

    def test_spanish_strip_irse(self):
        """Test stripping -irse suffix from Spanish reflexive verbs."""
        self.assertEqual(_strip_reflexive_pronoun("dormirse", "es"), "dormir")
        self.assertEqual(_strip_reflexive_pronoun("vestirse", "es"), "vestir")

    def test_spanish_no_reflexive(self):
        """Test Spanish non-reflexive words stay unchanged."""
        self.assertEqual(_strip_reflexive_pronoun("comer", "es"), "comer")
        self.assertEqual(_strip_reflexive_pronoun("ese", "es"), "ese")
        self.assertEqual(_strip_reflexive_pronoun("base", "es"), "base")

    # Unsupported language
    def test_unsupported_language_unchanged(self):
        """Test unsupported languages return word unchanged."""
        self.assertEqual(_strip_reflexive_pronoun("test word", "ja"), "test word")
        self.assertEqual(_strip_reflexive_pronoun("sich freuen", "unknown"), "sich freuen")


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
        self.assertEqual(_extract_gender_from_pos("masculin", "fr"), "le")
        self.assertEqual(_extract_gender_from_pos("féminin", "fr"), "la")

    def test_spanish_gender_extraction(self):
        """Test Spanish gender extraction from POS."""
        self.assertEqual(_extract_gender_from_pos("masculine noun", "es"), "el")
        self.assertEqual(_extract_gender_from_pos("feminine noun", "es"), "la")
        self.assertEqual(_extract_gender_from_pos("masculino", "es"), "el")
        self.assertEqual(_extract_gender_from_pos("femenino", "es"), "la")

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
        entry["senses"][0]["tags"] = ["masculin"]
        self.assertEqual(_extract_gender_from_senses(entry, "fr"), "le")
        entry["senses"][0]["tags"] = ["féminin"]
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
        entry["senses"][0]["tags"] = ["masculino"]
        self.assertEqual(_extract_gender_from_senses(entry, "es"), "el")
        entry["senses"][0]["tags"] = ["femenino"]
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


class TestDictionaryAPIResult(unittest.TestCase):
    """Test DictionaryAPIResult dataclass."""

    def test_result_to_dict(self):
        """Test DictionaryAPIResult.to_dict() method."""
        entries = [{"partOfSpeech": "noun", "senses": [{"definition": "Test definition"}]}]
        result = DictionaryAPIResult(
            definition="Test definition",
            pos="noun",
            phonetics="/test/",
            forms={"plural": "tests"},
            gender="der",
            all_entries=entries,
        )
        result_dict = result.to_dict()
        self.assertEqual(result_dict["definition"], "Test definition")
        self.assertEqual(result_dict["pos"], "noun")
        self.assertEqual(result_dict["phonetics"], "/test/")
        self.assertEqual(result_dict["forms"], {"plural": "tests"})
        self.assertEqual(result_dict["gender"], "der")
        self.assertEqual(result_dict["all_entries"], entries)
        self.assertNotIn("all_senses", result_dict)

    def test_result_to_dict_with_none_values(self):
        """Test to_dict with None values."""
        result = DictionaryAPIResult()
        result_dict = result.to_dict()
        self.assertIsNone(result_dict["definition"])
        self.assertIsNone(result_dict["pos"])
        self.assertIsNone(result_dict["phonetics"])
        self.assertIsNone(result_dict["forms"])
        self.assertIsNone(result_dict["gender"])
        self.assertIsNone(result_dict["all_entries"])


class TestExtractEntryMetadata(unittest.TestCase):
    """Test extract_entry_metadata helper function."""

    def test_extracts_full_metadata(self):
        """Test extracting all metadata fields from entry."""
        entry = {
            "partOfSpeech": "noun",
            "pronunciations": [{"type": "ipa", "text": "/hʊnt/"}],
            "senses": [
                {"definition": "dog, hound", "tags": ["masculine"]}
            ],
            "forms": [
                {"word": "Hundes", "tags": ["genitive"]},
                {"word": "Hunde", "tags": ["plural"]},
            ]
        }
        meta = extract_entry_metadata(entry, "de")
        self.assertEqual(meta["pos"], "noun")
        self.assertIsNone(meta["phonetics"])  # German doesn't support phonetics
        self.assertEqual(meta["forms"], {"genitive": "Hundes", "plural": "Hunde"})
        self.assertEqual(meta["gender"], "der")
        self.assertEqual(len(meta["senses"]), 1)

    def test_extracts_phonetics_for_english(self):
        """Test that phonetics are extracted for English (supports_phonetics=True)."""
        entry = {
            "partOfSpeech": "noun",
            "pronunciations": [{"type": "ipa", "text": "/dɒɡ/"}],
            "senses": [{"definition": "a domesticated animal"}],
        }
        meta = extract_entry_metadata(entry, "en")
        self.assertEqual(meta["phonetics"], "/dɒɡ/")

    def test_extracts_verb_metadata(self):
        """Test extracting verb metadata without gender."""
        entry = {
            "partOfSpeech": "verb",
            "senses": [{"definition": "to go"}],
            "forms": [
                {"word": "geht", "tags": ["present", "singular", "third-person"]},
            ]
        }
        meta = extract_entry_metadata(entry, "de")
        self.assertEqual(meta["pos"], "verb")
        self.assertIsNone(meta["gender"])
        self.assertEqual(meta["forms"], {"present": "geht"})

    def test_minimal_entry(self):
        """Test extracting metadata from minimal entry."""
        entry = {"partOfSpeech": "adjective"}
        meta = extract_entry_metadata(entry, "en")
        self.assertEqual(meta["pos"], "adjective")
        self.assertIsNone(meta["phonetics"])
        self.assertIsNone(meta["forms"])
        self.assertIsNone(meta["gender"])
        self.assertEqual(meta["senses"], [])

    def test_gender_fallback_to_pos(self):
        """Test gender extraction falls back to POS when senses lack tags."""
        entry = {
            "partOfSpeech": "masculine noun",
            "senses": [{"definition": "dog"}],
        }
        meta = extract_entry_metadata(entry, "de")
        self.assertEqual(meta["gender"], "der")

    def test_no_phonetics_for_german(self):
        """Test that phonetics are not extracted for German."""
        entry = {
            "partOfSpeech": "noun",
            "pronunciations": [{"type": "ipa", "text": "/hʊnt/"}],
            "senses": [{"definition": "dog"}],
        }
        meta = extract_entry_metadata(entry, "de")
        self.assertIsNone(meta["phonetics"])

    def test_no_phonetics_for_french(self):
        """Test that phonetics are not extracted for French."""
        entry = {
            "partOfSpeech": "noun",
            "pronunciations": [{"type": "ipa", "text": "/ʃjɛ̃/"}],
            "senses": [{"definition": "dog"}],
        }
        meta = extract_entry_metadata(entry, "fr")
        self.assertIsNone(meta["phonetics"])

    def test_no_phonetics_for_spanish(self):
        """Test that phonetics are not extracted for Spanish."""
        entry = {
            "partOfSpeech": "noun",
            "pronunciations": [{"type": "ipa", "text": "/ˈpe.ro/"}],
            "senses": [{"definition": "dog"}],
        }
        meta = extract_entry_metadata(entry, "es")
        self.assertIsNone(meta["phonetics"])

    def test_no_phonetics_for_unsupported(self):
        """Test that phonetics are not extracted for unsupported languages."""
        entry = {
            "partOfSpeech": "noun",
            "pronunciations": [{"type": "ipa", "text": "/test/"}],
            "senses": [{"definition": "test"}],
        }
        meta = extract_entry_metadata(entry, "ja")
        self.assertIsNone(meta["phonetics"])


class TestFetchFromFreeDictionaryApi(unittest.IsolatedAsyncioTestCase):
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
        self.assertIsNotNone(result.all_entries)
        self.assertEqual(len(result.all_entries), 1)
        self.assertEqual(result.all_entries[0]["partOfSpeech"], "noun")

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

        # Empty response has no entries, returns None
        self.assertIsNone(result)


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
        assert result.all_entries is not None
        assert len(result.all_entries) == 1
        assert result.all_entries[0]["senses"] == [{"definition": "Test definition"}]


if __name__ == '__main__':
    unittest.main()
