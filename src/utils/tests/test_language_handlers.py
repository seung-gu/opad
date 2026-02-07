"""Tests for language handler strategy pattern."""

import unittest

from ..language_handlers import (
    GermanHandler,
    FrenchHandler,
    SpanishHandler,
    DefaultHandler,
    get_language_handler,
)


class TestGermanHandler(unittest.TestCase):
    """Test German language handler."""

    def test_extract_gender_masculine(self):
        self.assertEqual(GermanHandler.extract_gender_from_pos("masculine noun"), "der")
        self.assertEqual(GermanHandler.extract_gender_from_pos("männlich"), "der")

    def test_extract_gender_feminine(self):
        self.assertEqual(GermanHandler.extract_gender_from_pos("feminine noun"), "die")
        self.assertEqual(GermanHandler.extract_gender_from_pos("weiblich"), "die")

    def test_extract_gender_neuter(self):
        self.assertEqual(GermanHandler.extract_gender_from_pos("neuter noun"), "das")
        self.assertEqual(GermanHandler.extract_gender_from_pos("sächlich"), "das")

    def test_extract_gender_from_pos_case_insensitive(self):
        self.assertEqual(GermanHandler.extract_gender_from_pos("MASCULINE NOUN"), "der")
        self.assertEqual(GermanHandler.extract_gender_from_pos("Feminine Noun"), "die")
        self.assertEqual(GermanHandler.extract_gender_from_pos("NEUTER"), "das")

    def test_extract_gender_from_pos_none_or_empty(self):
        self.assertIsNone(GermanHandler.extract_gender_from_pos(""))
        self.assertIsNone(GermanHandler.extract_gender_from_pos(None))

    def test_extract_gender_from_pos_no_gender(self):
        self.assertIsNone(GermanHandler.extract_gender_from_pos("noun"))
        self.assertIsNone(GermanHandler.extract_gender_from_pos("verb"))

    def test_extract_gender_from_tags(self):
        self.assertEqual(GermanHandler.extract_gender_from_tags(["masculine"]), "der")
        self.assertEqual(GermanHandler.extract_gender_from_tags(["feminine"]), "die")
        self.assertEqual(GermanHandler.extract_gender_from_tags(["neuter"]), "das")

    def test_extract_gender_from_tags_case_insensitive(self):
        self.assertEqual(GermanHandler.extract_gender_from_tags(["MASCULINE"]), "der")
        self.assertEqual(GermanHandler.extract_gender_from_tags(["Feminine"]), "die")
        self.assertEqual(GermanHandler.extract_gender_from_tags(["NEUTER"]), "das")

    def test_extract_gender_from_tags_empty(self):
        self.assertIsNone(GermanHandler.extract_gender_from_tags([]))

    def test_extract_gender_from_tags_no_gender(self):
        self.assertIsNone(GermanHandler.extract_gender_from_tags(["verb", "transitive"]))

    def test_strip_reflexive_sich(self):
        self.assertEqual(GermanHandler.strip_reflexive_pronoun("sich freuen"), "freuen")
        self.assertEqual(GermanHandler.strip_reflexive_pronoun("Sich setzen"), "setzen")

    def test_strip_reflexive_other(self):
        self.assertEqual(GermanHandler.strip_reflexive_pronoun("mich erinnern"), "erinnern")
        self.assertEqual(GermanHandler.strip_reflexive_pronoun("dich setzen"), "setzen")
        self.assertEqual(GermanHandler.strip_reflexive_pronoun("uns treffen"), "treffen")
        self.assertEqual(GermanHandler.strip_reflexive_pronoun("euch beeilen"), "beeilen")

    def test_no_reflexive(self):
        self.assertEqual(GermanHandler.strip_reflexive_pronoun("gehen"), "gehen")
        self.assertEqual(GermanHandler.strip_reflexive_pronoun("Haus"), "Haus")


class TestFrenchHandler(unittest.TestCase):
    """Test French language handler."""

    def test_extract_gender_masculine(self):
        self.assertEqual(FrenchHandler.extract_gender_from_pos("masculine noun"), "le")
        self.assertEqual(FrenchHandler.extract_gender_from_pos("masculin"), "le")

    def test_extract_gender_feminine(self):
        self.assertEqual(FrenchHandler.extract_gender_from_pos("feminine noun"), "la")
        self.assertEqual(FrenchHandler.extract_gender_from_pos("féminin"), "la")

    def test_extract_gender_from_pos_case_insensitive(self):
        self.assertEqual(FrenchHandler.extract_gender_from_pos("MASCULINE"), "le")
        self.assertEqual(FrenchHandler.extract_gender_from_pos("FÉMININ"), "la")

    def test_extract_gender_from_pos_none_or_empty(self):
        self.assertIsNone(FrenchHandler.extract_gender_from_pos(""))
        self.assertIsNone(FrenchHandler.extract_gender_from_pos(None))

    def test_extract_gender_from_pos_no_gender(self):
        self.assertIsNone(FrenchHandler.extract_gender_from_pos("noun"))
        self.assertIsNone(FrenchHandler.extract_gender_from_pos("verb"))

    def test_extract_gender_from_tags(self):
        self.assertEqual(FrenchHandler.extract_gender_from_tags(["masculine"]), "le")
        self.assertEqual(FrenchHandler.extract_gender_from_tags(["masculin"]), "le")
        self.assertEqual(FrenchHandler.extract_gender_from_tags(["feminine"]), "la")
        self.assertEqual(FrenchHandler.extract_gender_from_tags(["féminin"]), "la")

    def test_extract_gender_from_tags_empty(self):
        self.assertIsNone(FrenchHandler.extract_gender_from_tags([]))

    def test_strip_reflexive_se(self):
        self.assertEqual(FrenchHandler.strip_reflexive_pronoun("se lever"), "lever")
        self.assertEqual(FrenchHandler.strip_reflexive_pronoun("Se coucher"), "coucher")

    def test_strip_reflexive_s_apostrophe(self):
        self.assertEqual(FrenchHandler.strip_reflexive_pronoun("s'asseoir"), "asseoir")
        self.assertEqual(FrenchHandler.strip_reflexive_pronoun("S'habiller"), "habiller")

    def test_no_reflexive(self):
        self.assertEqual(FrenchHandler.strip_reflexive_pronoun("manger"), "manger")


class TestSpanishHandler(unittest.TestCase):
    """Test Spanish language handler."""

    def test_extract_gender_masculine(self):
        self.assertEqual(SpanishHandler.extract_gender_from_pos("masculine noun"), "el")
        self.assertEqual(SpanishHandler.extract_gender_from_pos("masculino"), "el")

    def test_extract_gender_feminine(self):
        self.assertEqual(SpanishHandler.extract_gender_from_pos("feminine noun"), "la")
        self.assertEqual(SpanishHandler.extract_gender_from_pos("femenino"), "la")

    def test_extract_gender_from_pos_case_insensitive(self):
        self.assertEqual(SpanishHandler.extract_gender_from_pos("MASCULINE"), "el")
        self.assertEqual(SpanishHandler.extract_gender_from_pos("FEMENINO"), "la")

    def test_extract_gender_from_pos_none_or_empty(self):
        self.assertIsNone(SpanishHandler.extract_gender_from_pos(""))
        self.assertIsNone(SpanishHandler.extract_gender_from_pos(None))

    def test_extract_gender_from_pos_no_gender(self):
        self.assertIsNone(SpanishHandler.extract_gender_from_pos("noun"))
        self.assertIsNone(SpanishHandler.extract_gender_from_pos("verb"))

    def test_extract_gender_from_tags(self):
        self.assertEqual(SpanishHandler.extract_gender_from_tags(["masculine"]), "el")
        self.assertEqual(SpanishHandler.extract_gender_from_tags(["masculino"]), "el")
        self.assertEqual(SpanishHandler.extract_gender_from_tags(["feminine"]), "la")
        self.assertEqual(SpanishHandler.extract_gender_from_tags(["femenino"]), "la")

    def test_extract_gender_from_tags_empty(self):
        self.assertIsNone(SpanishHandler.extract_gender_from_tags([]))

    def test_strip_reflexive_arse(self):
        self.assertEqual(SpanishHandler.strip_reflexive_pronoun("levantarse"), "levantar")
        self.assertEqual(SpanishHandler.strip_reflexive_pronoun("bañarse"), "bañar")

    def test_strip_reflexive_erse(self):
        self.assertEqual(SpanishHandler.strip_reflexive_pronoun("ponerse"), "poner")
        self.assertEqual(SpanishHandler.strip_reflexive_pronoun("moverse"), "mover")

    def test_strip_reflexive_irse(self):
        self.assertEqual(SpanishHandler.strip_reflexive_pronoun("dormirse"), "dormir")
        self.assertEqual(SpanishHandler.strip_reflexive_pronoun("vestirse"), "vestir")

    def test_no_reflexive(self):
        self.assertEqual(SpanishHandler.strip_reflexive_pronoun("comer"), "comer")
        self.assertEqual(SpanishHandler.strip_reflexive_pronoun("ese"), "ese")
        self.assertEqual(SpanishHandler.strip_reflexive_pronoun("base"), "base")


class TestDefaultHandler(unittest.TestCase):
    """Test default language handler."""

    def test_returns_none_for_gender(self):
        self.assertIsNone(DefaultHandler.extract_gender_from_pos("masculine noun"))
        self.assertIsNone(DefaultHandler.extract_gender_from_tags(["masculine"]))

    def test_no_strip(self):
        self.assertEqual(DefaultHandler.strip_reflexive_pronoun("test word"), "test word")
        self.assertEqual(DefaultHandler.strip_reflexive_pronoun("sich freuen"), "sich freuen")


class TestGetLanguageHandler(unittest.TestCase):
    """Test language handler registry."""

    def test_german(self):
        self.assertEqual(get_language_handler("de"), GermanHandler)

    def test_french(self):
        self.assertEqual(get_language_handler("fr"), FrenchHandler)

    def test_spanish(self):
        self.assertEqual(get_language_handler("es"), SpanishHandler)

    def test_unsupported_returns_default(self):
        self.assertEqual(get_language_handler("en"), DefaultHandler)
        self.assertEqual(get_language_handler("ja"), DefaultHandler)
        self.assertEqual(get_language_handler("unknown"), DefaultHandler)

    def test_empty_string_returns_default(self):
        self.assertEqual(get_language_handler(""), DefaultHandler)


if __name__ == "__main__":
    unittest.main()
