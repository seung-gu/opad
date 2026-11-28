"""Unit tests for CEFR level filtering.

Tests cover:
1. CEFRLevel.range() - levels from min_level to max_level, both included
2. CEFRLevel.next() - the level one above
"""

import unittest

from domain.model.cefr import CEFRLevel

ALL = CEFRLevel.ALL


class TestCEFRLevelRange(unittest.TestCase):
    """Test cases for CEFRLevel.range static method."""

    # ── One argument: from A1 to max_level ──

    def test_max_level_b2(self):
        self.assertEqual(CEFRLevel.range("B2"), ["A1", "A2", "B1", "B2"])

    def test_max_level_a1(self):
        self.assertEqual(CEFRLevel.range("A1"), ["A1"])

    def test_max_level_c2(self):
        self.assertEqual(CEFRLevel.range("C2"), ALL)

    # ── With min_level: from min_level to max_level ──

    def test_min_level_and_max_level(self):
        self.assertEqual(CEFRLevel.range("B2", min_level="A2"), ["A2", "B1", "B2"])

    def test_min_level_equals_max_level(self):
        self.assertEqual(CEFRLevel.range("B1", min_level="B1"), ["B1"])

    def test_min_level_above_max_level_is_empty(self):
        self.assertEqual(CEFRLevel.range("A2", min_level="C1"), [])

    # ── None / outside A1-C2 → all levels ──

    def test_none(self):
        self.assertEqual(CEFRLevel.range(None), ALL)

    def test_empty_string(self):
        self.assertEqual(CEFRLevel.range(""), ALL)

    def test_invalid(self):
        self.assertEqual(CEFRLevel.range("X1"), ALL)

    def test_lowercase_counts_as_invalid(self):
        self.assertEqual(CEFRLevel.range("b1"), ALL)

    def test_invalid_min_level(self):
        self.assertEqual(CEFRLevel.range("B2", min_level="X1"), ALL)


class TestCEFRLevelNext(unittest.TestCase):
    """Test cases for CEFRLevel.next static method."""

    def test_next_a1(self):
        self.assertEqual(CEFRLevel.next("A1"), "A2")

    def test_next_b1(self):
        self.assertEqual(CEFRLevel.next("B1"), "B2")

    def test_next_c2_stays_c2(self):
        self.assertEqual(CEFRLevel.next("C2"), "C2")

    def test_next_none(self):
        self.assertIsNone(CEFRLevel.next(None))

    def test_next_invalid(self):
        self.assertIsNone(CEFRLevel.next("X1"))


class TestVocabularyFilterRange(unittest.TestCase):
    """The article generator asks for words from A1 to one level above the user's."""

    def test_b1_user_gets_a1_to_b2(self):
        self.assertEqual(CEFRLevel.range(CEFRLevel.next("B1")), ["A1", "A2", "B1", "B2"])

    def test_a1_user_gets_a1_to_a2(self):
        self.assertEqual(CEFRLevel.range(CEFRLevel.next("A1")), ["A1", "A2"])

    def test_c1_and_c2_users_get_all(self):
        self.assertEqual(CEFRLevel.range(CEFRLevel.next("C1")), ALL)
        self.assertEqual(CEFRLevel.range(CEFRLevel.next("C2")), ALL)

    def test_no_level_gets_all(self):
        self.assertEqual(CEFRLevel.range(CEFRLevel.next(None)), ALL)


if __name__ == "__main__":
    unittest.main()
