"""Unit tests for CEFR level filtering.

Tests cover:
1. CEFRLevel.range() - CEFR level range calculation
"""

import unittest

from domain.model.cefr import CEFRLevel


ALL = CEFRLevel.ALL


class TestCEFRLevelRange(unittest.TestCase):
    """Test cases for CEFRLevel.range static method."""

    # ── Default behavior (max_above=1) ──

    def test_default_b1(self):
        self.assertEqual(CEFRLevel.range('B1'), ['A1', 'A2', 'B1', 'B2'])

    def test_default_a1(self):
        self.assertEqual(CEFRLevel.range('A1'), ['A1', 'A2'])

    def test_default_c2(self):
        self.assertEqual(CEFRLevel.range('C2'), ALL)

    def test_default_a2(self):
        self.assertEqual(CEFRLevel.range('A2'), ['A1', 'A2', 'B1'])

    def test_default_c1(self):
        self.assertEqual(CEFRLevel.range('C1'), ALL)

    # ── max_above variations ──

    def test_max_above_0(self):
        self.assertEqual(CEFRLevel.range('B1', max_above=0), ['A1', 'A2', 'B1'])

    def test_max_above_2(self):
        self.assertEqual(CEFRLevel.range('A1', max_above=2), ['A1', 'A2', 'B1'])

    def test_max_above_exceeds(self):
        self.assertEqual(CEFRLevel.range('B2', max_above=10), ALL)

    def test_a1_max_above_0(self):
        self.assertEqual(CEFRLevel.range('A1', max_above=0), ['A1'])

    def test_b2_max_above_0(self):
        self.assertEqual(CEFRLevel.range('B2', max_above=0), ['A1', 'A2', 'B1', 'B2'])

    # ── None / invalid / empty ──

    def test_none_target(self):
        self.assertEqual(CEFRLevel.range(None), ALL)

    def test_invalid_target(self):
        self.assertEqual(CEFRLevel.range('X1'), ALL)

    def test_empty_string(self):
        self.assertEqual(CEFRLevel.range(''), ALL)

    def test_whitespace_only(self):
        self.assertEqual(CEFRLevel.range('   '), ALL)

    def test_trailing_whitespace(self):
        self.assertEqual(CEFRLevel.range('A1 '), ALL)

    def test_case_insensitive(self):
        self.assertEqual(CEFRLevel.range('b1'), ['A1', 'A2', 'B1', 'B2'])


if __name__ == '__main__':
    unittest.main()
