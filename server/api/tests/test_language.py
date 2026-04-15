"""Tests for Language Value Object.

Tests cover Language immutability, gender_articles freezing, language instance
codes, and LANGUAGES registry structure and contents.
"""

import unittest
from types import MappingProxyType

from domain.model.language import (
    Language,
    GERMAN,
    ENGLISH,
    FRENCH,
    SPANISH,
    ITALIAN,
    KOREAN,
    LANGUAGES,
)


class TestLanguageImmutability(unittest.TestCase):
    """Test Language Value Object immutability."""

    def test_language_is_frozen_dataclass(self):
        """Test that Language instances are frozen (immutable)."""
        with self.assertRaises((TypeError, AttributeError)):
            GERMAN.name = "Deutsch"

    def test_language_code_immutable(self):
        """Test that language code cannot be modified."""
        with self.assertRaises((TypeError, AttributeError)):
            ENGLISH.code = "en-US"

    def test_language_reflexive_prefixes_immutable(self):
        """Test that reflexive_prefixes tuple cannot be modified."""
        with self.assertRaises((TypeError, AttributeError)):
            FRENCH.reflexive_prefixes = ("se ", "s'", "m'")

    def test_gender_articles_is_mapping_proxy_type(self):
        """Test that gender_articles is a MappingProxyType (immutable)."""
        self.assertIsInstance(GERMAN.gender_articles, MappingProxyType)

    def test_gender_articles_mutation_raises_type_error(self):
        """Test attempting to mutate gender_articles raises TypeError."""
        with self.assertRaises(TypeError):
            GERMAN.gender_articles["test"] = "test_value"

    def test_gender_articles_cannot_be_deleted(self):
        """Test attempting to delete from gender_articles raises error."""
        # MappingProxyType doesn't have a __delitem__ method
        with self.assertRaises(TypeError):
            del GERMAN.gender_articles["masculine"]

    def test_gender_articles_dict_converted_to_proxy_at_init(self):
        """Test that dict passed to Language is converted to MappingProxyType."""
        lang = Language(
            name="TestLang",
            code="tl",
            gender_articles={"test": "value"}
        )
        self.assertIsInstance(lang.gender_articles, MappingProxyType)
        self.assertEqual(lang.gender_articles["test"], "value")

    def test_gender_articles_proxy_already_passed_unchanged(self):
        """Test that MappingProxyType passed to Language stays as MappingProxyType."""
        proxy = MappingProxyType({"test": "value"})
        lang = Language(
            name="TestLang",
            code="tl",
            gender_articles=proxy
        )
        self.assertIsInstance(lang.gender_articles, MappingProxyType)
        self.assertEqual(lang.gender_articles["test"], "value")


class TestLanguageInstances(unittest.TestCase):
    """Test Language instance codes and properties."""

    def test_german_code(self):
        """Test German language code is 'de'."""
        self.assertEqual(GERMAN.code, "de")

    def test_english_code(self):
        """Test English language code is 'en'."""
        self.assertEqual(ENGLISH.code, "en")

    def test_french_code(self):
        """Test French language code is 'fr'."""
        self.assertEqual(FRENCH.code, "fr")

    def test_spanish_code(self):
        """Test Spanish language code is 'es'."""
        self.assertEqual(SPANISH.code, "es")

    def test_italian_code(self):
        """Test Italian language code is 'it'."""
        self.assertEqual(ITALIAN.code, "it")

    def test_korean_code(self):
        """Test Korean language code is 'ko'."""
        self.assertEqual(KOREAN.code, "ko")

    def test_german_has_gender_articles(self):
        """Test German has gender articles configured."""
        self.assertGreater(len(GERMAN.gender_articles), 0)
        self.assertEqual(GERMAN.gender_articles["masculine"], "der")
        self.assertEqual(GERMAN.gender_articles["feminine"], "die")
        self.assertEqual(GERMAN.gender_articles["neuter"], "das")

    def test_german_has_reflexive_prefixes(self):
        """Test German has reflexive prefix patterns."""
        self.assertGreater(len(GERMAN.reflexive_prefixes), 0)
        self.assertIn("sich ", GERMAN.reflexive_prefixes)

    def test_french_has_gender_articles(self):
        """Test French has gender articles configured."""
        self.assertGreater(len(FRENCH.gender_articles), 0)
        self.assertEqual(FRENCH.gender_articles["masculine"], "le")
        self.assertEqual(FRENCH.gender_articles["feminine"], "la")

    def test_french_has_reflexive_prefixes(self):
        """Test French has reflexive prefix patterns."""
        self.assertGreater(len(FRENCH.reflexive_prefixes), 0)
        self.assertIn("se ", FRENCH.reflexive_prefixes)

    def test_spanish_has_gender_articles(self):
        """Test Spanish has gender articles configured."""
        self.assertGreater(len(SPANISH.gender_articles), 0)
        self.assertEqual(SPANISH.gender_articles["masculine"], "el")
        self.assertEqual(SPANISH.gender_articles["feminine"], "la")

    def test_spanish_has_reflexive_suffixes(self):
        """Test Spanish has reflexive suffix patterns."""
        self.assertGreater(len(SPANISH.reflexive_suffixes), 0)
        self.assertIn("arse", SPANISH.reflexive_suffixes)

    def test_english_no_gender_articles(self):
        """Test English has no gender articles."""
        self.assertEqual(len(ENGLISH.gender_articles), 0)

    def test_english_no_reflexive_patterns(self):
        """Test English has no reflexive prefix or suffix patterns."""
        self.assertEqual(len(ENGLISH.reflexive_prefixes), 0)
        self.assertEqual(len(ENGLISH.reflexive_suffixes), 0)

    def test_italian_no_gender_articles(self):
        """Test Italian has no gender articles configured."""
        self.assertEqual(len(ITALIAN.gender_articles), 0)

    def test_korean_no_gender_articles(self):
        """Test Korean has no gender articles."""
        self.assertEqual(len(KOREAN.gender_articles), 0)


class TestLanguagesRegistry(unittest.TestCase):
    """Test LANGUAGES registry structure and contents."""

    def test_languages_registry_has_six_entries(self):
        """Test LANGUAGES registry contains exactly 6 languages."""
        self.assertEqual(len(LANGUAGES), 6)

    def test_languages_registry_keys_are_names(self):
        """Test LANGUAGES registry keys are language names."""
        self.assertIn("German", LANGUAGES)
        self.assertIn("English", LANGUAGES)
        self.assertIn("French", LANGUAGES)
        self.assertIn("Spanish", LANGUAGES)
        self.assertIn("Italian", LANGUAGES)
        self.assertIn("Korean", LANGUAGES)

    def test_languages_registry_contains_german(self):
        """Test LANGUAGES registry contains German instance."""
        self.assertIs(LANGUAGES["German"], GERMAN)

    def test_languages_registry_contains_english(self):
        """Test LANGUAGES registry contains English instance."""
        self.assertIs(LANGUAGES["English"], ENGLISH)

    def test_languages_registry_contains_french(self):
        """Test LANGUAGES registry contains French instance."""
        self.assertIs(LANGUAGES["French"], FRENCH)

    def test_languages_registry_contains_spanish(self):
        """Test LANGUAGES registry contains Spanish instance."""
        self.assertIs(LANGUAGES["Spanish"], SPANISH)

    def test_languages_registry_contains_italian(self):
        """Test LANGUAGES registry contains Italian instance."""
        self.assertIs(LANGUAGES["Italian"], ITALIAN)

    def test_languages_registry_contains_korean(self):
        """Test LANGUAGES registry contains Korean instance."""
        self.assertIs(LANGUAGES["Korean"], KOREAN)

    def test_languages_registry_values_have_matching_names(self):
        """Test all Language instances in registry have matching names."""
        for name, lang in LANGUAGES.items():
            self.assertEqual(lang.name, name)

    def test_languages_registry_all_have_codes(self):
        """Test all languages in registry have non-empty codes."""
        for name, lang in LANGUAGES.items():
            self.assertIsNotNone(lang.code)
            self.assertTrue(len(lang.code) > 0)


if __name__ == '__main__':
    unittest.main()
