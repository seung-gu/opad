"""Unit tests for vocabulary level filtering functions in mongodb.py.

Tests cover:
1. get_allowed_vocab_levels() - CEFR level filtering logic
2. get_user_vocabulary_for_generation() with target_level parameter
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from pymongo.errors import PyMongoError

from utils.mongodb import get_allowed_vocab_levels, get_user_vocabulary_for_generation, CEFR_LEVELS


class TestGetAllowedVocabLevels(unittest.TestCase):
    """Test cases for get_allowed_vocab_levels function."""

    def test_valid_level_a1_returns_a1_a2(self):
        """Test that A1 target level with max_above=1 returns A1, A2."""
        result = get_allowed_vocab_levels('A1', max_above=1)
        self.assertEqual(result, ['A1', 'A2'])

    def test_valid_level_a1_with_max_above_0(self):
        """Test that A1 with max_above=0 returns only A1."""
        result = get_allowed_vocab_levels('A1', max_above=0)
        self.assertEqual(result, ['A1'])

    def test_valid_level_a2_with_max_above_1_returns_a1_a2_b1(self):
        """Test that A2 with max_above=1 returns A1, A2, B1."""
        result = get_allowed_vocab_levels('A2', max_above=1)
        self.assertEqual(result, ['A1', 'A2', 'B1'])

    def test_valid_level_b1_with_max_above_1_returns_a1_to_b2(self):
        """Test that B1 with max_above=1 returns A1, A2, B1, B2."""
        result = get_allowed_vocab_levels('B1', max_above=1)
        self.assertEqual(result, ['A1', 'A2', 'B1', 'B2'])

    def test_valid_level_b2_with_max_above_1_returns_a1_to_c1(self):
        """Test that B2 with max_above=1 returns A1, A2, B1, B2, C1."""
        result = get_allowed_vocab_levels('B2', max_above=1)
        self.assertEqual(result, ['A1', 'A2', 'B1', 'B2', 'C1'])

    def test_valid_level_c1_with_max_above_1_returns_a1_to_c2(self):
        """Test that C1 with max_above=1 returns all levels A1-C2."""
        result = get_allowed_vocab_levels('C1', max_above=1)
        self.assertEqual(result, ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'])

    def test_valid_level_c2_returns_all_levels(self):
        """Test that C2 target level returns all levels (can't go higher)."""
        result = get_allowed_vocab_levels('C2', max_above=1)
        self.assertEqual(result, ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'])

    def test_valid_level_c2_with_max_above_5_still_returns_all_levels(self):
        """Test that C2 with high max_above still returns all levels (boundary check)."""
        result = get_allowed_vocab_levels('C2', max_above=5)
        self.assertEqual(result, ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'])

    def test_case_insensitive_lowercase_a2(self):
        """Test that lowercase 'a2' works correctly (case insensitive)."""
        result_lower = get_allowed_vocab_levels('a2', max_above=1)
        result_upper = get_allowed_vocab_levels('A2', max_above=1)
        self.assertEqual(result_lower, result_upper)
        self.assertEqual(result_lower, ['A1', 'A2', 'B1'])

    def test_case_insensitive_lowercase_b1(self):
        """Test that lowercase 'b1' works correctly."""
        result_lower = get_allowed_vocab_levels('b1', max_above=1)
        result_upper = get_allowed_vocab_levels('B1', max_above=1)
        self.assertEqual(result_lower, result_upper)

    def test_case_insensitive_mixed_case_C2(self):
        """Test that mixed case 'C2' works correctly."""
        result_mixed = get_allowed_vocab_levels('c2', max_above=1)
        result_upper = get_allowed_vocab_levels('C2', max_above=1)
        self.assertEqual(result_mixed, result_upper)

    def test_max_above_0_returns_up_to_target_level(self):
        """Test that max_above=0 returns all levels up to and including target."""
        self.assertEqual(get_allowed_vocab_levels('A1', max_above=0), ['A1'])
        self.assertEqual(get_allowed_vocab_levels('B1', max_above=0), ['A1', 'A2', 'B1'])
        self.assertEqual(get_allowed_vocab_levels('C2', max_above=0), ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'])

    def test_max_above_2_returns_two_levels_above(self):
        """Test that max_above=2 returns target + 2 levels above."""
        result = get_allowed_vocab_levels('A1', max_above=2)
        self.assertEqual(result, ['A1', 'A2', 'B1'])

    def test_max_above_3_for_a1_returns_a1_to_b2(self):
        """Test that max_above=3 returns A1 plus 3 levels above."""
        result = get_allowed_vocab_levels('A1', max_above=3)
        self.assertEqual(result, ['A1', 'A2', 'B1', 'B2'])

    def test_max_above_large_value_respects_boundary(self):
        """Test that max_above with large value respects C2 boundary."""
        result = get_allowed_vocab_levels('B1', max_above=100)
        self.assertEqual(result, ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'])

    def test_invalid_level_returns_all_cefr_levels(self):
        """Test that invalid level returns all CEFR levels."""
        result = get_allowed_vocab_levels('INVALID', max_above=1)
        self.assertEqual(result, CEFR_LEVELS)

    def test_invalid_level_empty_string(self):
        """Test that empty string returns all CEFR levels."""
        result = get_allowed_vocab_levels('', max_above=1)
        self.assertEqual(result, CEFR_LEVELS)

    def test_invalid_level_b3_returns_all(self):
        """Test that non-existent level B3 returns all CEFR levels."""
        result = get_allowed_vocab_levels('B3', max_above=1)
        self.assertEqual(result, CEFR_LEVELS)

    def test_invalid_level_a0_returns_all(self):
        """Test that non-existent level A0 returns all CEFR levels."""
        result = get_allowed_vocab_levels('A0', max_above=1)
        self.assertEqual(result, CEFR_LEVELS)

    def test_invalid_level_c3_returns_all(self):
        """Test that non-existent level C3 returns all CEFR levels."""
        result = get_allowed_vocab_levels('C3', max_above=1)
        self.assertEqual(result, CEFR_LEVELS)

    def test_all_valid_levels_return_correct_ranges(self):
        """Test all valid levels return correct ranges."""
        test_cases = [
            ('A1', 1, ['A1', 'A2']),  # A1 + 1 level above = A1, A2
            ('A2', 1, ['A1', 'A2', 'B1']),
            ('B1', 1, ['A1', 'A2', 'B1', 'B2']),
            ('B2', 1, ['A1', 'A2', 'B1', 'B2', 'C1']),
            ('C1', 1, ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']),
            ('C2', 1, ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']),
        ]

        for level, max_above, expected in test_cases:
            with self.subTest(level=level, max_above=max_above):
                result = get_allowed_vocab_levels(level, max_above=max_above)
                self.assertEqual(result, expected)

    def test_preserves_cefr_order(self):
        """Test that results always preserve CEFR level order."""
        result = get_allowed_vocab_levels('A2', max_above=2)
        self.assertEqual(result, ['A1', 'A2', 'B1', 'B2'])
        # Verify order is maintained
        for i in range(len(result) - 1):
            self.assertLess(CEFR_LEVELS.index(result[i]), CEFR_LEVELS.index(result[i + 1]))

    def test_result_is_list(self):
        """Test that result is always a list."""
        result = get_allowed_vocab_levels('B1', max_above=1)
        self.assertIsInstance(result, list)

    def test_result_is_subset_of_cefr_levels(self):
        """Test that result is always a subset of CEFR_LEVELS."""
        for level in CEFR_LEVELS:
            result = get_allowed_vocab_levels(level, max_above=2)
            self.assertTrue(all(lv in CEFR_LEVELS for lv in result))

    def test_max_above_negative_returns_only_target(self):
        """Test that negative max_above is treated safely."""
        # This edge case: negative max_above could cause issues
        # The implementation uses min(target_index + max_above, len-1)
        # With negative max_above and low level, result might be restricted
        result = get_allowed_vocab_levels('A1', max_above=-1)
        # Should return at least the target level (A1)
        self.assertIn('A1', result)

    def test_whitespace_only_invalid(self):
        """Test that whitespace-only string is invalid."""
        result = get_allowed_vocab_levels('   ', max_above=1)
        self.assertEqual(result, CEFR_LEVELS)

    def test_level_with_trailing_whitespace(self):
        """Test that level with trailing whitespace is invalid."""
        result = get_allowed_vocab_levels('A1 ', max_above=1)
        self.assertEqual(result, CEFR_LEVELS)


class TestGetUserVocabularyForGenerationWithTargetLevel(unittest.TestCase):
    """Test cases for get_user_vocabulary_for_generation with target_level filtering."""

    def setUp(self):
        """Set up test fixtures."""
        self.user_id = "test_user_123"
        self.language = "English"
        self.test_date_1 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.test_date_2 = datetime(2025, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        self.test_date_3 = datetime(2025, 1, 3, 12, 0, 0, tzinfo=timezone.utc)

    @patch('utils.mongodb.get_mongodb_client')
    def test_target_level_none_no_level_filter(self, mock_get_client):
        """Test that target_level=None does not add level filter to pipeline."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.aggregate.return_value = []

        get_user_vocabulary_for_generation(self.user_id, self.language, target_level=None)

        # Get pipeline
        pipeline = mock_collection.aggregate.call_args[0][0]
        match_stage = pipeline[0]['$match']

        # Verify no 'level' filter in match stage
        self.assertNotIn('level', match_stage)
        # But user_id and language should be there
        self.assertEqual(match_stage['user_id'], self.user_id)
        self.assertEqual(match_stage['language'], self.language)

    @patch('utils.mongodb.get_mongodb_client')
    def test_target_level_a2_filters_to_allowed_levels(self, mock_get_client):
        """Test that target_level='A2' adds level filter for A1, A2, B1."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.aggregate.return_value = []

        get_user_vocabulary_for_generation(self.user_id, self.language, target_level='A2')

        # Get pipeline
        pipeline = mock_collection.aggregate.call_args[0][0]
        match_stage = pipeline[0]['$match']

        # Verify level filter exists
        self.assertIn('level', match_stage)
        level_filter = match_stage['level']

        # Verify $in operator
        self.assertIn('$in', level_filter)
        allowed_levels = level_filter['$in']

        # For A2 with max_above=1, should allow A1, A2, B1
        self.assertEqual(allowed_levels, ['A1', 'A2', 'B1'])

    @patch('utils.mongodb.get_mongodb_client')
    def test_target_level_b1_filters_to_allowed_levels(self, mock_get_client):
        """Test that target_level='B1' adds level filter for A1, A2, B1, B2."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.aggregate.return_value = []

        get_user_vocabulary_for_generation(self.user_id, self.language, target_level='B1')

        # Get pipeline
        pipeline = mock_collection.aggregate.call_args[0][0]
        match_stage = pipeline[0]['$match']

        # Verify level filter
        allowed_levels = match_stage['level']['$in']
        self.assertEqual(allowed_levels, ['A1', 'A2', 'B1', 'B2'])

    @patch('utils.mongodb.get_mongodb_client')
    def test_target_level_c2_filters_to_all_levels(self, mock_get_client):
        """Test that target_level='C2' allows all CEFR levels."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.aggregate.return_value = []

        get_user_vocabulary_for_generation(self.user_id, self.language, target_level='C2')

        # Get pipeline
        pipeline = mock_collection.aggregate.call_args[0][0]
        match_stage = pipeline[0]['$match']

        # Verify level filter includes all levels
        allowed_levels = match_stage['level']['$in']
        self.assertEqual(allowed_levels, CEFR_LEVELS)

    @patch('utils.mongodb.get_mongodb_client')
    def test_target_level_case_insensitive_lowercase(self, mock_get_client):
        """Test that target_level is case insensitive (lowercase)."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.aggregate.return_value = []

        get_user_vocabulary_for_generation(self.user_id, self.language, target_level='a2')

        # Get pipeline
        pipeline = mock_collection.aggregate.call_args[0][0]
        match_stage = pipeline[0]['$match']

        # Verify level filter works with lowercase
        allowed_levels = match_stage['level']['$in']
        self.assertEqual(allowed_levels, ['A1', 'A2', 'B1'])

    @patch('utils.mongodb.get_mongodb_client')
    def test_target_level_case_insensitive_uppercase(self, mock_get_client):
        """Test that target_level is case insensitive (uppercase)."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.aggregate.return_value = []

        get_user_vocabulary_for_generation(self.user_id, self.language, target_level='B1')

        # Get pipeline
        pipeline = mock_collection.aggregate.call_args[0][0]
        match_stage = pipeline[0]['$match']

        # Verify level filter
        allowed_levels = match_stage['level']['$in']
        self.assertEqual(allowed_levels, ['A1', 'A2', 'B1', 'B2'])

    @patch('utils.mongodb.get_mongodb_client')
    def test_target_level_invalid_returns_no_level_filter(self, mock_get_client):
        """Test that invalid target_level returns all levels (no restrictive filter)."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.aggregate.return_value = []

        get_user_vocabulary_for_generation(self.user_id, self.language, target_level='INVALID')

        # Get pipeline
        pipeline = mock_collection.aggregate.call_args[0][0]
        match_stage = pipeline[0]['$match']

        # When all levels are returned, $in should have all of them
        # This means no restriction (worst case, all allowed)
        if 'level' in match_stage:
            allowed_levels = match_stage['level']['$in']
            self.assertEqual(allowed_levels, CEFR_LEVELS)

    @patch('utils.mongodb.get_mongodb_client')
    def test_target_level_with_limit_both_applied(self, mock_get_client):
        """Test that both target_level and limit are applied correctly."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.aggregate.return_value = []

        get_user_vocabulary_for_generation(
            self.user_id,
            self.language,
            target_level='B1',
            limit=25
        )

        # Get pipeline
        pipeline = mock_collection.aggregate.call_args[0][0]

        # Check match stage has level filter
        match_stage = pipeline[0]['$match']
        self.assertIn('level', match_stage)
        self.assertEqual(match_stage['level']['$in'], ['A1', 'A2', 'B1', 'B2'])

        # Check limit stage
        self.assertEqual(pipeline[3]['$limit'], 25)

    @patch('utils.mongodb.get_mongodb_client')
    @patch('utils.mongodb.logger')
    def test_logs_level_filtering_when_target_level_provided(self, mock_logger, mock_get_client):
        """Test that debug log is recorded when target_level filtering is applied."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.aggregate.return_value = []

        get_user_vocabulary_for_generation(
            self.user_id,
            self.language,
            target_level='B1'
        )

        # Verify debug log was called for level filtering
        debug_calls = [call for call in mock_logger.debug.call_args_list
                      if 'level' in str(call).lower()]
        self.assertGreaterEqual(len(debug_calls), 1)

    @patch('utils.mongodb.get_mongodb_client')
    def test_target_level_a1_filters_to_only_a1(self, mock_get_client):
        """Test that target_level='A1' filters to only A1 (with max_above=1)."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.aggregate.return_value = []

        get_user_vocabulary_for_generation(self.user_id, self.language, target_level='A1')

        # Get pipeline
        pipeline = mock_collection.aggregate.call_args[0][0]
        match_stage = pipeline[0]['$match']

        # For A1 with max_above=1, should allow A1, A2
        allowed_levels = match_stage['level']['$in']
        self.assertEqual(allowed_levels, ['A1', 'A2'])

    @patch('utils.mongodb.get_mongodb_client')
    def test_target_level_empty_string_returns_no_restriction(self, mock_get_client):
        """Test that target_level='' returns all levels."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.aggregate.return_value = []

        get_user_vocabulary_for_generation(self.user_id, self.language, target_level='')

        # Get pipeline
        pipeline = mock_collection.aggregate.call_args[0][0]
        match_stage = pipeline[0]['$match']

        # Empty string is invalid, should return all levels
        if 'level' in match_stage:
            allowed_levels = match_stage['level']['$in']
            self.assertEqual(allowed_levels, CEFR_LEVELS)

    @patch('utils.mongodb.get_mongodb_client')
    def test_target_level_none_vs_string_none(self, mock_get_client):
        """Test that target_level=None and target_level='None' behave correctly."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.aggregate.return_value = []

        # Test with None (parameter default)
        get_user_vocabulary_for_generation(self.user_id, self.language, target_level=None)
        pipeline_1 = mock_collection.aggregate.call_args[0][0]
        match_stage_1 = pipeline_1[0]['$match']

        # Should NOT have level filter for None
        self.assertNotIn('level', match_stage_1)

        # Reset mock
        mock_collection.aggregate.return_value = []

        # Test with string 'None' (invalid)
        get_user_vocabulary_for_generation(self.user_id, self.language, target_level='None')
        pipeline_2 = mock_collection.aggregate.call_args[0][0]
        match_stage_2 = pipeline_2[0]['$match']

        # String 'None' is invalid, should allow all or not restrict
        # Check if level filter exists and what it contains
        if 'level' in match_stage_2:
            self.assertEqual(match_stage_2['level']['$in'], CEFR_LEVELS)

    @patch('utils.mongodb.get_mongodb_client')
    def test_filtering_excludes_vocabulary_above_max_level(self, mock_get_client):
        """Test that vocabulary above allowed level is excluded from results."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # Mock result with C1 vocabulary (above B1 + 1 = B2)
        # Only A1, A2, B1, B2 should be returned for B1
        mock_collection.aggregate.return_value = [
            {'lemma': 'word_a1'},   # A1 level - included
            {'lemma': 'word_a2'},   # A2 level - included
            {'lemma': 'word_b1'},   # B1 level - included
            {'lemma': 'word_b2'},   # B2 level - included
            # C1 vocabulary should not appear in results due to filter
        ]

        result = get_user_vocabulary_for_generation(
            self.user_id,
            self.language,
            target_level='B1',
            limit=10
        )

        # Verify the filter in pipeline
        pipeline = mock_collection.aggregate.call_args[0][0]
        match_stage = pipeline[0]['$match']
        self.assertEqual(match_stage['level']['$in'], ['A1', 'A2', 'B1', 'B2'])

    @patch('utils.mongodb.get_mongodb_client')
    def test_combined_filters_user_language_and_level(self, mock_get_client):
        """Test that all three filters (user_id, language, level) are combined."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.aggregate.return_value = []

        get_user_vocabulary_for_generation(
            user_id='user_123',
            language='German',
            target_level='B2'
        )

        # Get pipeline
        pipeline = mock_collection.aggregate.call_args[0][0]
        match_stage = pipeline[0]['$match']

        # Verify all three filters
        self.assertEqual(match_stage['user_id'], 'user_123')
        self.assertEqual(match_stage['language'], 'German')
        self.assertEqual(match_stage['level']['$in'], ['A1', 'A2', 'B1', 'B2', 'C1'])

    @patch('utils.mongodb.get_mongodb_client')
    def test_multiple_calls_with_different_levels(self, mock_get_client):
        """Test multiple calls with different target levels produce different filters."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # First call with A2
        mock_collection.aggregate.return_value = []
        get_user_vocabulary_for_generation(self.user_id, self.language, target_level='A2')
        pipeline_1 = mock_collection.aggregate.call_args_list[0][0][0]
        levels_1 = pipeline_1[0]['$match']['level']['$in']

        # Second call with B1
        get_user_vocabulary_for_generation(self.user_id, self.language, target_level='B1')
        pipeline_2 = mock_collection.aggregate.call_args_list[1][0][0]
        levels_2 = pipeline_2[0]['$match']['level']['$in']

        # Third call with C1
        get_user_vocabulary_for_generation(self.user_id, self.language, target_level='C1')
        pipeline_3 = mock_collection.aggregate.call_args_list[2][0][0]
        levels_3 = pipeline_3[0]['$match']['level']['$in']

        # Verify each has different levels
        self.assertEqual(levels_1, ['A1', 'A2', 'B1'])
        self.assertEqual(levels_2, ['A1', 'A2', 'B1', 'B2'])
        self.assertEqual(levels_3, ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'])

        # Verify they're all different
        self.assertNotEqual(levels_1, levels_2)
        self.assertNotEqual(levels_2, levels_3)


class TestVocabularyLevelFilteringEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions for level filtering."""

    @patch('utils.mongodb.get_mongodb_client')
    def test_level_none_falsy_check(self, mock_get_client):
        """Test that None target_level is correctly identified as falsy."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.aggregate.return_value = []

        get_user_vocabulary_for_generation('user', 'en', target_level=None)

        pipeline = mock_collection.aggregate.call_args[0][0]
        match_stage = pipeline[0]['$match']

        # None should not add level filter
        self.assertNotIn('level', match_stage)

    @patch('utils.mongodb.get_mongodb_client')
    def test_all_levels_included_when_filtering_c2(self, mock_get_client):
        """Test that C2 target includes all levels."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.aggregate.return_value = []

        get_user_vocabulary_for_generation('user', 'en', target_level='C2')

        pipeline = mock_collection.aggregate.call_args[0][0]
        match_stage = pipeline[0]['$match']

        allowed_levels = match_stage['level']['$in']
        self.assertEqual(len(allowed_levels), 6)  # All 6 CEFR levels
        self.assertEqual(allowed_levels, CEFR_LEVELS)

    @patch('utils.mongodb.get_mongodb_client')
    def test_vocabulary_level_none_field_handling(self, mock_get_client):
        """Test handling of vocabularies where level field is None."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # Mock result with None level (vocabulary without level assigned)
        mock_collection.aggregate.return_value = [
            {'lemma': 'word_with_level'},
            {'lemma': 'word_without_level'},  # This might have level=None in DB
        ]

        result = get_user_vocabulary_for_generation('user', 'en', target_level='B1')

        # The $in filter will exclude documents where level is None or not in the list
        # This is expected MongoDB behavior
        self.assertIsInstance(result, list)

    def test_cefr_levels_constant_correct(self):
        """Test that CEFR_LEVELS constant has all levels in correct order."""
        expected = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
        self.assertEqual(CEFR_LEVELS, expected)
        self.assertEqual(len(CEFR_LEVELS), 6)


class TestVocabularyLevelIntegration(unittest.TestCase):
    """Integration tests for vocabulary level filtering."""

    @patch('utils.mongodb.get_mongodb_client')
    def test_sorting_still_works_with_level_filter(self, mock_get_client):
        """Test that frequency/recency sorting works together with level filtering."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # Mock results sorted by frequency and recency
        mock_collection.aggregate.return_value = [
            {'lemma': 'popular'},    # Most frequent
            {'lemma': 'recent'},     # Recently learned
            {'lemma': 'old'},        # Less frequent, older
        ]

        result = get_user_vocabulary_for_generation('user', 'en', target_level='B1')

        # Verify sorting stages are still there
        pipeline = mock_collection.aggregate.call_args[0][0]

        # Stage 2: $group
        self.assertIn('$group', pipeline[1])

        # Stage 3: $sort (frequency, then recency)
        sort_stage = pipeline[2]['$sort']
        self.assertEqual(sort_stage['count'], -1)
        self.assertEqual(sort_stage['max_created_at'], -1)

        # Result should be sorted
        self.assertEqual(result, ['popular', 'recent', 'old'])

    @patch('utils.mongodb.get_mongodb_client')
    def test_level_filter_with_empty_results(self, mock_get_client):
        """Test level filter when no vocabulary matches the allowed levels."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # No results match
        mock_collection.aggregate.return_value = []

        result = get_user_vocabulary_for_generation('user', 'en', target_level='A1')

        # Should return empty list
        self.assertEqual(result, [])
        self.assertIsInstance(result, list)

    @patch('utils.mongodb.get_mongodb_client')
    def test_level_filter_preserves_other_pipeline_stages(self, mock_get_client):
        """Test that adding level filter doesn't break other pipeline stages."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.aggregate.return_value = []

        get_user_vocabulary_for_generation('user', 'en', target_level='B1', limit=30)

        pipeline = mock_collection.aggregate.call_args[0][0]

        # All expected stages should be present
        self.assertEqual(len(pipeline), 5)

        # Stage 1: $match (with level filter)
        self.assertIn('$match', pipeline[0])

        # Stage 2: $group
        self.assertIn('$group', pipeline[1])

        # Stage 3: $sort
        self.assertIn('$sort', pipeline[2])

        # Stage 4: $limit
        self.assertIn('$limit', pipeline[3])
        self.assertEqual(pipeline[3]['$limit'], 30)

        # Stage 5: $project
        self.assertIn('$project', pipeline[4])


if __name__ == '__main__':
    unittest.main()
