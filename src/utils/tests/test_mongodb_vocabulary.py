"""Unit tests for get_user_vocabulary_for_generation function in mongodb.py."""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from pymongo.errors import PyMongoError

from src.utils.mongodb import get_user_vocabulary_for_generation


class TestGetUserVocabularyForGeneration(unittest.TestCase):
    """Test cases for get_user_vocabulary_for_generation function."""

    def setUp(self):
        """Set up test fixtures."""
        self.user_id = "test_user_123"
        self.language = "English"
        self.test_date_1 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.test_date_2 = datetime(2025, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        self.test_date_3 = datetime(2025, 1, 3, 12, 0, 0, tzinfo=timezone.utc)

    @patch('src.utils.mongodb.get_mongodb_client')
    def test_returns_lemmas_sorted_by_frequency_desc(self, mock_get_client):
        """Test that lemmas are returned sorted by frequency (descending)."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # Mock aggregation result: different frequencies
        # 'agent' appears 5 times, 'test' appears 3 times, 'code' appears 1 time
        mock_collection.aggregate.return_value = [
            {'lemma': 'agent'},  # count=5 (highest)
            {'lemma': 'test'},   # count=3
            {'lemma': 'code'}    # count=1 (lowest)
        ]

        result = get_user_vocabulary_for_generation(self.user_id, self.language)

        # Verify correct order by frequency
        self.assertEqual(result, ['agent', 'test', 'code'])

        # Verify aggregation pipeline was called with correct parameters
        mock_collection.aggregate.assert_called_once()
        pipeline = mock_collection.aggregate.call_args[0][0]

        # Verify match stage
        self.assertEqual(pipeline[0]['$match']['user_id'], self.user_id)
        self.assertEqual(pipeline[0]['$match']['language'], self.language)

        # Verify sort stage (count descending, max_created_at descending)
        self.assertEqual(pipeline[2]['$sort']['count'], -1)
        self.assertEqual(pipeline[2]['$sort']['max_created_at'], -1)

        # Verify limit stage (default 50)
        self.assertEqual(pipeline[3]['$limit'], 50)

    @patch('src.utils.mongodb.get_mongodb_client')
    def test_same_frequency_sorted_by_recency_desc(self, mock_get_client):
        """Test that lemmas with same frequency are sorted by recency (most recent first)."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # Mock aggregation result: same frequency (count=2), different created_at
        # Order should be: newest first (date_3), then older (date_2), then oldest (date_1)
        mock_collection.aggregate.return_value = [
            {'lemma': 'zebra'},    # count=2, max_created_at=date_3 (most recent)
            {'lemma': 'yellow'},   # count=2, max_created_at=date_2
            {'lemma': 'xray'}      # count=2, max_created_at=date_1 (oldest)
        ]

        result = get_user_vocabulary_for_generation(self.user_id, self.language)

        # Verify correct order: most recent first for same frequency
        self.assertEqual(result, ['zebra', 'yellow', 'xray'])

    @patch('src.utils.mongodb.get_mongodb_client')
    def test_language_filtering_works_correctly(self, mock_get_client):
        """Test that language filter works correctly."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        mock_collection.aggregate.return_value = [
            {'lemma': 'hello'},
            {'lemma': 'world'}
        ]

        # Test with English
        result_english = get_user_vocabulary_for_generation(self.user_id, "English")
        self.assertEqual(result_english, ['hello', 'world'])

        # Verify correct language in match stage
        pipeline_call_1 = mock_collection.aggregate.call_args_list[0][0][0]
        self.assertEqual(pipeline_call_1[0]['$match']['language'], "English")

        # Test with German
        mock_collection.aggregate.return_value = [
            {'lemma': 'hallo'},
            {'lemma': 'welt'}
        ]
        result_german = get_user_vocabulary_for_generation(self.user_id, "German")
        self.assertEqual(result_german, ['hallo', 'welt'])

        # Verify correct language in match stage
        pipeline_call_2 = mock_collection.aggregate.call_args_list[1][0][0]
        self.assertEqual(pipeline_call_2[0]['$match']['language'], "German")

    @patch('src.utils.mongodb.get_mongodb_client')
    def test_limit_parameter_works(self, mock_get_client):
        """Test that limit parameter correctly limits results."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        mock_collection.aggregate.return_value = [
            {'lemma': f'word{i}'} for i in range(10)
        ]

        # Test with custom limit of 10
        result = get_user_vocabulary_for_generation(self.user_id, self.language, limit=10)

        # Verify result length matches limit
        self.assertEqual(len(result), 10)

        # Verify limit in aggregation pipeline
        pipeline = mock_collection.aggregate.call_args[0][0]
        self.assertEqual(pipeline[3]['$limit'], 10)

        # Test with limit of 5
        mock_collection.aggregate.return_value = [
            {'lemma': f'word{i}'} for i in range(5)
        ]
        result = get_user_vocabulary_for_generation(self.user_id, self.language, limit=5)
        self.assertEqual(len(result), 5)

        pipeline = mock_collection.aggregate.call_args[0][0]
        self.assertEqual(pipeline[3]['$limit'], 5)

    @patch('src.utils.mongodb.get_mongodb_client')
    def test_default_limit_is_50(self, mock_get_client):
        """Test that default limit is 50 when not specified."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        mock_collection.aggregate.return_value = []

        # Call without limit parameter
        get_user_vocabulary_for_generation(self.user_id, self.language)

        # Verify default limit of 50 in aggregation pipeline
        pipeline = mock_collection.aggregate.call_args[0][0]
        self.assertEqual(pipeline[3]['$limit'], 50)

    @patch('src.utils.mongodb.get_mongodb_client')
    def test_empty_result_when_no_vocabularies_found(self, mock_get_client):
        """Test that empty list is returned when no vocabularies match filters."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # Mock empty aggregation result
        mock_collection.aggregate.return_value = []

        result = get_user_vocabulary_for_generation(self.user_id, self.language)

        # Verify empty list returned
        self.assertEqual(result, [])
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @patch('src.utils.mongodb.get_mongodb_client')
    def test_returns_empty_list_when_mongodb_client_fails(self, mock_get_client):
        """Test that empty list is returned when MongoDB client connection fails."""
        # Mock get_mongodb_client returning None (connection failure)
        mock_get_client.return_value = None

        result = get_user_vocabulary_for_generation(self.user_id, self.language)

        # Verify empty list returned
        self.assertEqual(result, [])
        self.assertIsInstance(result, list)

    @patch('src.utils.mongodb.get_mongodb_client')
    def test_returns_empty_list_on_pymongo_error(self, mock_get_client):
        """Test that empty list is returned when PyMongoError occurs during aggregation."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # Mock aggregation raising PyMongoError
        mock_collection.aggregate.side_effect = PyMongoError("Database connection lost")

        result = get_user_vocabulary_for_generation(self.user_id, self.language)

        # Verify empty list returned on error
        self.assertEqual(result, [])
        self.assertIsInstance(result, list)

    @patch('src.utils.mongodb.get_mongodb_client')
    def test_aggregation_pipeline_structure(self, mock_get_client):
        """Test that aggregation pipeline has correct structure and stages."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.aggregate.return_value = []

        get_user_vocabulary_for_generation(self.user_id, self.language, limit=25)

        # Get the pipeline argument
        pipeline = mock_collection.aggregate.call_args[0][0]

        # Verify pipeline has 5 stages
        self.assertEqual(len(pipeline), 5)

        # Stage 1: $match
        self.assertIn('$match', pipeline[0])
        self.assertEqual(pipeline[0]['$match']['user_id'], self.user_id)
        self.assertEqual(pipeline[0]['$match']['language'], self.language)

        # Stage 2: $group
        self.assertIn('$group', pipeline[1])
        self.assertEqual(pipeline[1]['$group']['_id'], '$lemma')
        self.assertIn('count', pipeline[1]['$group'])
        self.assertEqual(pipeline[1]['$group']['count'], {'$sum': 1})
        self.assertIn('max_created_at', pipeline[1]['$group'])
        self.assertEqual(pipeline[1]['$group']['max_created_at'], {'$max': '$created_at'})

        # Stage 3: $sort
        self.assertIn('$sort', pipeline[2])
        self.assertEqual(pipeline[2]['$sort']['count'], -1)
        self.assertEqual(pipeline[2]['$sort']['max_created_at'], -1)

        # Stage 4: $limit
        self.assertIn('$limit', pipeline[3])
        self.assertEqual(pipeline[3]['$limit'], 25)

        # Stage 5: $project
        self.assertIn('$project', pipeline[4])
        self.assertEqual(pipeline[4]['$project']['_id'], 0)
        self.assertEqual(pipeline[4]['$project']['lemma'], '$_id')

    @patch('src.utils.mongodb.get_mongodb_client')
    def test_mixed_frequency_and_recency_sorting(self, mock_get_client):
        """Test complex scenario with mixed frequencies and recencies."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # Mock result with mixed frequencies:
        # - 'popular' appears 10 times (highest frequency)
        # - 'recent1' and 'recent2' both appear 5 times, but recent1 is newer
        # - 'old' appears 1 time (lowest frequency)
        mock_collection.aggregate.return_value = [
            {'lemma': 'popular'},  # count=10
            {'lemma': 'recent1'},  # count=5, max_created_at=date_3
            {'lemma': 'recent2'},  # count=5, max_created_at=date_2
            {'lemma': 'old'}       # count=1
        ]

        result = get_user_vocabulary_for_generation(self.user_id, self.language)

        # Verify correct sorting: frequency first, then recency
        self.assertEqual(result, ['popular', 'recent1', 'recent2', 'old'])

    @patch('src.utils.mongodb.get_mongodb_client')
    def test_handles_special_characters_in_lemmas(self, mock_get_client):
        """Test that function handles lemmas with special characters correctly."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # Mock result with special characters in lemmas
        mock_collection.aggregate.return_value = [
            {'lemma': "it's"},
            {'lemma': 'über'},
            {'lemma': 'café'},
            {'lemma': 'naïve'}
        ]

        result = get_user_vocabulary_for_generation(self.user_id, self.language)

        # Verify special characters are preserved
        self.assertEqual(result, ["it's", 'über', 'café', 'naïve'])

    @patch('src.utils.mongodb.get_mongodb_client')
    def test_different_users_get_different_vocabularies(self, mock_get_client):
        """Test that different user_ids retrieve different vocabularies."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # User 1's vocabulary
        mock_collection.aggregate.return_value = [
            {'lemma': 'user1_word1'},
            {'lemma': 'user1_word2'}
        ]
        result1 = get_user_vocabulary_for_generation("user1", self.language)

        # Verify user_id in first call
        pipeline_call_1 = mock_collection.aggregate.call_args_list[0][0][0]
        self.assertEqual(pipeline_call_1[0]['$match']['user_id'], "user1")

        # User 2's vocabulary
        mock_collection.aggregate.return_value = [
            {'lemma': 'user2_word1'},
            {'lemma': 'user2_word2'}
        ]
        result2 = get_user_vocabulary_for_generation("user2", self.language)

        # Verify user_id in second call
        pipeline_call_2 = mock_collection.aggregate.call_args_list[1][0][0]
        self.assertEqual(pipeline_call_2[0]['$match']['user_id'], "user2")

        # Verify results are different
        self.assertNotEqual(result1, result2)

    @patch('src.utils.mongodb.get_mongodb_client')
    @patch('src.utils.mongodb.logger')
    def test_logs_success_with_correct_info(self, mock_logger, mock_get_client):
        """Test that function logs success with correct information."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        mock_collection.aggregate.return_value = [
            {'lemma': 'word1'},
            {'lemma': 'word2'},
            {'lemma': 'word3'}
        ]

        result = get_user_vocabulary_for_generation(self.user_id, self.language)

        # Verify logger.info was called with correct message and extra data
        mock_logger.info.assert_called_once_with(
            "Retrieved vocabulary for generation",
            extra={
                "userId": self.user_id,
                "language": self.language,
                "count": 3
            }
        )

    @patch('src.utils.mongodb.get_mongodb_client')
    @patch('src.utils.mongodb.logger')
    def test_logs_error_on_pymongo_exception(self, mock_logger, mock_get_client):
        """Test that function logs error when PyMongoError occurs."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # Mock aggregation raising PyMongoError
        error_message = "Connection timeout"
        mock_collection.aggregate.side_effect = PyMongoError(error_message)

        result = get_user_vocabulary_for_generation(self.user_id, self.language)

        # Verify logger.error was called with correct message and extra data
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        self.assertEqual(call_args[0][0], "Failed to get vocabulary for generation")
        self.assertEqual(call_args[1]['extra']['userId'], self.user_id)
        self.assertEqual(call_args[1]['extra']['language'], self.language)
        self.assertIn('error', call_args[1]['extra'])


if __name__ == '__main__':
    unittest.main()
