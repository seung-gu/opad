"""Unit tests for vocabulary level filtering functions.

Tests cover:
1. get_allowed_vocab_levels() - CEFR level filtering logic
"""

import unittest

from services.vocabulary_service import CEFR_LEVELS, get_allowed_vocab_levels


class TestGetAllowedVocabLevels(unittest.TestCase):
    """Test cases for get_allowed_vocab_levels function."""

    def test_valid_level_a1_returns_a1_a2(self):
        """Test A1 with max_above=1 returns A1, A2."""
        result = get_allowed_vocab_levels('A1', max_above=1)
        self.assertEqual(result, ['A1', 'A2'])

    def test_valid_level_b1_returns_a1_to_b2(self):
        """Test B1 with max_above=1 returns A1 through B2."""
        result = get_allowed_vocab_levels('B1', max_above=1)
        self.assertEqual(result, ['A1', 'A2', 'B1', 'B2'])

    def test_valid_level_c2_returns_all(self):
        """Test C2 (highest) with max_above=1 returns all levels."""
        result = get_allowed_vocab_levels('C2', max_above=1)
        self.assertEqual(result, CEFR_LEVELS)

    def test_max_above_0_returns_only_target_and_below(self):
        """Test max_above=0 returns only target level and below."""
        result = get_allowed_vocab_levels('B1', max_above=0)
        self.assertEqual(result, ['A1', 'A2', 'B1'])

    def test_max_above_2_returns_wider_range(self):
        """Test max_above=2 returns wider range above target."""
        result = get_allowed_vocab_levels('A1', max_above=2)
        self.assertEqual(result, ['A1', 'A2', 'B1'])

    def test_max_above_larger_than_remaining_returns_all(self):
        """Test max_above larger than remaining levels returns all."""
        result = get_allowed_vocab_levels('B2', max_above=10)
        self.assertEqual(result, CEFR_LEVELS)

    def test_none_target_level_returns_all(self):
        """Test None target_level returns all CEFR levels."""
        result = get_allowed_vocab_levels(None, max_above=1)
        self.assertEqual(result, CEFR_LEVELS)

    def test_invalid_level_returns_all(self):
        """Test invalid level string returns all CEFR levels."""
        result = get_allowed_vocab_levels('X1', max_above=1)
        self.assertEqual(result, CEFR_LEVELS)

    def test_empty_string_returns_all(self):
        """Test empty string returns all CEFR levels."""
        result = get_allowed_vocab_levels('', max_above=1)
        self.assertEqual(result, CEFR_LEVELS)

    def test_case_insensitive(self):
        """Test case-insensitive level matching."""
        result = get_allowed_vocab_levels('b1', max_above=1)
        self.assertEqual(result, ['A1', 'A2', 'B1', 'B2'])

    def test_a2_max_above_1(self):
        """Test A2 with max_above=1."""
        result = get_allowed_vocab_levels('A2', max_above=1)
        self.assertEqual(result, ['A1', 'A2', 'B1'])

    def test_c1_max_above_1(self):
        """Test C1 with max_above=1."""
        result = get_allowed_vocab_levels('C1', max_above=1)
        self.assertEqual(result, ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'])

    def test_b2_max_above_0(self):
        """Test B2 with max_above=0."""
        result = get_allowed_vocab_levels('B2', max_above=0)
        self.assertEqual(result, ['A1', 'A2', 'B1', 'B2'])

    def test_a1_max_above_0(self):
        """Test A1 with max_above=0 returns only A1."""
        result = get_allowed_vocab_levels('A1', max_above=0)
        self.assertEqual(result, ['A1'])

    def test_default_max_above(self):
        """Test default max_above value."""
        result = get_allowed_vocab_levels('B1')
        self.assertEqual(result, ['A1', 'A2', 'B1', 'B2'])

    def test_whitespace_only_returns_all(self):
        """Test that whitespace-only string is invalid."""
        result = get_allowed_vocab_levels('   ', max_above=1)
        self.assertEqual(result, CEFR_LEVELS)

    def test_level_with_trailing_whitespace(self):
        """Test that level with trailing whitespace is invalid."""
        result = get_allowed_vocab_levels('A1 ', max_above=1)
        self.assertEqual(result, CEFR_LEVELS)


if __name__ == '__main__':
    unittest.main()
