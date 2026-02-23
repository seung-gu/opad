"""Tests for Free Dictionary API parsing utilities and Language Value Object.

Tests cover language lookup, gender extraction, phonetics, forms parsing,
and reflexive pronoun stripping with proper edge cases.
"""

import unittest

from adapter.external.free_dictionary import (
    _extract_gender_from_pos,
    _extract_gender_from_senses,
    _extract_phonetics,
    _extract_forms,
)
from domain.model.language import get_language, LANGUAGES, GERMAN, FRENCH, SPANISH


class TestGetLanguage(unittest.TestCase):
    """Test language lookup."""

    def test_supported_german(self):
        """Test German language lookup."""
        self.assertEqual(get_language("German").code, "de")

    def test_supported_english(self):
        """Test English language lookup."""
        self.assertEqual(get_language("English").code, "en")

    def test_supported_french(self):
        """Test French language lookup."""
        self.assertEqual(get_language("French").code, "fr")

    def test_supported_spanish(self):
        """Test Spanish language lookup."""
        self.assertEqual(get_language("Spanish").code, "es")

    def test_supported_italian(self):
        """Test Italian language lookup."""
        self.assertEqual(get_language("Italian").code, "it")

    def test_supported_korean(self):
        """Test Korean language lookup."""
        self.assertEqual(get_language("Korean").code, "ko")

    def test_unsupported_language(self):
        """Test unsupported language returns None."""
        self.assertIsNone(get_language("Japanese"))

    def test_case_sensitive(self):
        """Test that language names are case-sensitive."""
        self.assertIsNone(get_language("german"))
        self.assertIsNone(get_language("GERMAN"))

    def test_empty_string(self):
        """Test empty string returns None."""
        self.assertIsNone(get_language(""))

    def test_all_supported_languages(self):
        """Test all languages in LANGUAGES registry."""
        for name, lang in LANGUAGES.items():
            self.assertEqual(get_language(name).code, lang.code)


class TestStripReflexive(unittest.TestCase):
    """Test Language.strip_reflexive() for API lookup."""

    # German
    def test_strip_sich_german(self):
        """Test stripping 'sich' from German reflexive verbs."""
        self.assertEqual(GERMAN.strip_reflexive("sich gewöhnen"), "gewöhnen")

    def test_strip_sich_case_insensitive(self):
        """Test case-insensitive stripping."""
        self.assertEqual(GERMAN.strip_reflexive("Sich freuen"), "freuen")

    def test_no_reflexive_unchanged(self):
        """Test non-reflexive verbs remain unchanged."""
        self.assertEqual(GERMAN.strip_reflexive("gehen"), "gehen")

    def test_english_no_strip(self):
        """Test English doesn't strip reflexive pronouns."""
        from domain.model.language import ENGLISH
        self.assertEqual(ENGLISH.strip_reflexive("sich test"), "sich test")

    def test_other_pronouns(self):
        """Test other reflexive pronouns are stripped."""
        self.assertEqual(GERMAN.strip_reflexive("mich erinnern"), "erinnern")
        self.assertEqual(GERMAN.strip_reflexive("dich setzen"), "setzen")

    def test_german_uns_euch(self):
        """Test German uns/euch reflexive pronouns."""
        self.assertEqual(GERMAN.strip_reflexive("uns treffen"), "treffen")
        self.assertEqual(GERMAN.strip_reflexive("euch beeilen"), "beeilen")

    def test_german_non_reflexive_noun(self):
        """Test German non-reflexive words stay unchanged."""
        self.assertEqual(GERMAN.strip_reflexive("Haus"), "Haus")

    # French
    def test_french_strip_se(self):
        """Test stripping 'se' from French reflexive verbs."""
        self.assertEqual(FRENCH.strip_reflexive("se lever"), "lever")
        self.assertEqual(FRENCH.strip_reflexive("Se coucher"), "coucher")

    def test_french_strip_s_apostrophe(self):
        """Test stripping s' from French reflexive verbs."""
        self.assertEqual(FRENCH.strip_reflexive("s'asseoir"), "asseoir")
        self.assertEqual(FRENCH.strip_reflexive("S'habiller"), "habiller")

    def test_french_no_reflexive(self):
        """Test French non-reflexive verbs stay unchanged."""
        self.assertEqual(FRENCH.strip_reflexive("manger"), "manger")

    # Spanish
    def test_spanish_strip_arse(self):
        """Test stripping -arse suffix from Spanish reflexive verbs."""
        self.assertEqual(SPANISH.strip_reflexive("levantarse"), "levantar")
        self.assertEqual(SPANISH.strip_reflexive("bañarse"), "bañar")

    def test_spanish_strip_erse(self):
        """Test stripping -erse suffix from Spanish reflexive verbs."""
        self.assertEqual(SPANISH.strip_reflexive("ponerse"), "poner")
        self.assertEqual(SPANISH.strip_reflexive("moverse"), "mover")

    def test_spanish_strip_irse(self):
        """Test stripping -irse suffix from Spanish reflexive verbs."""
        self.assertEqual(SPANISH.strip_reflexive("dormirse"), "dormir")
        self.assertEqual(SPANISH.strip_reflexive("vestirse"), "vestir")

    def test_spanish_no_reflexive(self):
        """Test Spanish non-reflexive words stay unchanged."""
        self.assertEqual(SPANISH.strip_reflexive("comer"), "comer")
        self.assertEqual(SPANISH.strip_reflexive("ese"), "ese")
        self.assertEqual(SPANISH.strip_reflexive("base"), "base")


class TestExtractGenderFromPos(unittest.TestCase):
    """Test grammatical gender extraction from part of speech."""

    def test_masculine_noun_german(self):
        """Test masculine noun returns 'der'."""
        self.assertEqual(_extract_gender_from_pos("masculine noun", GERMAN), "der")

    def test_feminine_noun_german(self):
        """Test feminine noun returns 'die'."""
        self.assertEqual(_extract_gender_from_pos("feminine noun", GERMAN), "die")

    def test_neuter_noun_german(self):
        """Test neuter noun returns 'das'."""
        self.assertEqual(_extract_gender_from_pos("neuter noun", GERMAN), "das")

    def test_german_label_masculine(self):
        """Test German label for masculine (männlich)."""
        self.assertEqual(_extract_gender_from_pos("männlich noun", GERMAN), "der")

    def test_german_label_feminine(self):
        """Test German label for feminine (weiblich)."""
        self.assertEqual(_extract_gender_from_pos("weiblich noun", GERMAN), "die")

    def test_german_label_neuter(self):
        """Test German label for neuter (sächlich)."""
        self.assertEqual(_extract_gender_from_pos("sächlich noun", GERMAN), "das")

    def test_case_insensitive(self):
        """Test gender extraction is case-insensitive."""
        self.assertEqual(_extract_gender_from_pos("MASCULINE NOUN", GERMAN), "der")
        self.assertEqual(_extract_gender_from_pos("Feminine Noun", GERMAN), "die")

    def test_non_gendered_language_returns_none(self):
        """Test languages without gender support return None."""
        from domain.model.language import ENGLISH
        self.assertIsNone(_extract_gender_from_pos("masculine noun", ENGLISH))

    def test_french_gender_extraction(self):
        """Test French gender extraction from POS."""
        self.assertEqual(_extract_gender_from_pos("masculine noun", FRENCH), "le")
        self.assertEqual(_extract_gender_from_pos("feminine noun", FRENCH), "la")
        self.assertEqual(_extract_gender_from_pos("masculin", FRENCH), "le")
        self.assertEqual(_extract_gender_from_pos("féminin", FRENCH), "la")

    def test_spanish_gender_extraction(self):
        """Test Spanish gender extraction from POS."""
        self.assertEqual(_extract_gender_from_pos("masculine noun", SPANISH), "el")
        self.assertEqual(_extract_gender_from_pos("feminine noun", SPANISH), "la")
        self.assertEqual(_extract_gender_from_pos("masculino", SPANISH), "el")
        self.assertEqual(_extract_gender_from_pos("femenino", SPANISH), "la")

    def test_non_noun_german_returns_none(self):
        """Test non-noun parts of speech return None."""
        self.assertIsNone(_extract_gender_from_pos("verb", GERMAN))
        self.assertIsNone(_extract_gender_from_pos("adjective", GERMAN))
        self.assertIsNone(_extract_gender_from_pos("adverb", GERMAN))

    def test_empty_pos_returns_none(self):
        """Test empty part of speech returns None."""
        self.assertIsNone(_extract_gender_from_pos("", GERMAN))

    def test_none_pos_returns_none(self):
        """Test None part of speech returns None."""
        self.assertIsNone(_extract_gender_from_pos(None, GERMAN))

    def test_no_gender_indicator_returns_none(self):
        """Test part of speech without gender indicator returns None."""
        self.assertIsNone(_extract_gender_from_pos("noun", GERMAN))
        self.assertIsNone(_extract_gender_from_pos("regular noun", GERMAN))


class TestExtractGenderFromSenses(unittest.TestCase):
    """Test grammatical gender extraction from senses tags."""

    def test_masculine_tag_german(self):
        """Test masculine tag returns 'der'."""
        entry = {
            "senses": [
                {"definition": "dog", "tags": ["masculine"]}
            ]
        }
        self.assertEqual(_extract_gender_from_senses(entry, GERMAN), "der")

    def test_feminine_tag_german(self):
        """Test feminine tag returns 'die'."""
        entry = {
            "senses": [
                {"definition": "cat", "tags": ["feminine"]}
            ]
        }
        self.assertEqual(_extract_gender_from_senses(entry, GERMAN), "die")

    def test_neuter_tag_german(self):
        """Test neuter tag returns 'das'."""
        entry = {
            "senses": [
                {"definition": "child", "tags": ["neuter"]}
            ]
        }
        self.assertEqual(_extract_gender_from_senses(entry, GERMAN), "das")

    def test_case_insensitive(self):
        """Test gender extraction is case-insensitive."""
        entry = {
            "senses": [
                {"definition": "test", "tags": ["MASCULINE"]}
            ]
        }
        self.assertEqual(_extract_gender_from_senses(entry, GERMAN), "der")

    def test_non_gendered_language_returns_none(self):
        """Test languages without gender support return None."""
        from domain.model.language import ENGLISH
        entry = {
            "senses": [
                {"definition": "test", "tags": ["masculine"]}
            ]
        }
        self.assertIsNone(_extract_gender_from_senses(entry, ENGLISH))

    def test_french_gender_from_senses(self):
        """Test French gender extraction from senses tags."""
        entry = {
            "senses": [
                {"definition": "test", "tags": ["masculine"]}
            ]
        }
        self.assertEqual(_extract_gender_from_senses(entry, FRENCH), "le")
        entry["senses"][0]["tags"] = ["feminine"]
        self.assertEqual(_extract_gender_from_senses(entry, FRENCH), "la")
        entry["senses"][0]["tags"] = ["masculin"]
        self.assertEqual(_extract_gender_from_senses(entry, FRENCH), "le")
        entry["senses"][0]["tags"] = ["féminin"]
        self.assertEqual(_extract_gender_from_senses(entry, FRENCH), "la")

    def test_spanish_gender_from_senses(self):
        """Test Spanish gender extraction from senses tags."""
        entry = {
            "senses": [
                {"definition": "test", "tags": ["masculine"]}
            ]
        }
        self.assertEqual(_extract_gender_from_senses(entry, SPANISH), "el")
        entry["senses"][0]["tags"] = ["feminine"]
        self.assertEqual(_extract_gender_from_senses(entry, SPANISH), "la")
        entry["senses"][0]["tags"] = ["masculino"]
        self.assertEqual(_extract_gender_from_senses(entry, SPANISH), "el")
        entry["senses"][0]["tags"] = ["femenino"]
        self.assertEqual(_extract_gender_from_senses(entry, SPANISH), "la")

    def test_no_senses_returns_none(self):
        """Test entry with no senses returns None."""
        entry = {"senses": []}
        self.assertIsNone(_extract_gender_from_senses(entry, GERMAN))

    def test_no_tags_returns_none(self):
        """Test sense without tags returns None."""
        entry = {
            "senses": [
                {"definition": "test"}
            ]
        }
        self.assertIsNone(_extract_gender_from_senses(entry, GERMAN))

    def test_no_gender_tag_returns_none(self):
        """Test sense with non-gender tags returns None."""
        entry = {
            "senses": [
                {"definition": "test", "tags": ["verb", "transitive"]}
            ]
        }
        self.assertIsNone(_extract_gender_from_senses(entry, GERMAN))


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


if __name__ == '__main__':
    unittest.main()
