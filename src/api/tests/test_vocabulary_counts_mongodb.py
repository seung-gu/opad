"""Unit tests for get_vocabulary_counts MongoDB function."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.mongodb import get_vocabulary_counts


class TestGetVocabularyCounts(unittest.TestCase):
    """Test cases for get_vocabulary_counts function."""

    def setUp(self):
        """Set up test fixtures."""
        self.user_id = "test-user-123"
        self.sample_vocab_data = [
            {
                '_id': {'language': 'English', 'lemma': 'test'},
                'count': 5,
                'article_ids': ['article-1', 'article-2'],
                'vocabulary_id': 'vocab-1',
                'article_id': 'article-1',
                'definition': 'a procedure',
                'sentence': 'This is a test.',
                'word': 'testing',
                'created_at': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                'related_words': ['test', 'testing'],
                'span_id': 'span-1',
                'user_id': 'test-user-123'
            },
            {
                '_id': {'language': 'English', 'lemma': 'run'},
                'count': 3,
                'article_ids': ['article-3'],
                'vocabulary_id': 'vocab-2',
                'article_id': 'article-3',
                'definition': 'to move quickly',
                'sentence': 'I run fast.',
                'word': 'running',
                'created_at': datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
                'related_words': None,
                'span_id': None,
                'user_id': 'test-user-123'
            }
        ]

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabulary_counts_success(self, mock_get_client):
        """Test successful retrieval of vocabulary counts."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        mock_get_client.return_value = mock_client
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.aggregate.return_value = self.sample_vocab_data

        result = get_vocabulary_counts(
            language='English',
            user_id=self.user_id,
            skip=0,
            limit=100
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['lemma'], 'test')
        self.assertEqual(result[0]['count'], 5)
        self.assertEqual(result[0]['language'], 'English')
        self.assertEqual(result[1]['lemma'], 'run')
        self.assertEqual(result[1]['count'], 3)

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabulary_counts_with_language_filter(self, mock_get_client):
        """Test vocabulary counts with language filter."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        mock_get_client.return_value = mock_client
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.aggregate.return_value = []

        result = get_vocabulary_counts(
            language='German',
            user_id=self.user_id,
            skip=0,
            limit=100
        )

        # Verify aggregation pipeline includes language filter
        call_args = mock_collection.aggregate.call_args[0][0]
        self.assertTrue(any('$match' in stage for stage in call_args))
        match_stage = next(stage for stage in call_args if '$match' in stage)
        self.assertEqual(match_stage['$match']['language'], 'German')

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabulary_counts_with_user_filter(self, mock_get_client):
        """Test vocabulary counts with user_id filter."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        mock_get_client.return_value = mock_client
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.aggregate.return_value = []

        result = get_vocabulary_counts(
            language=None,
            user_id='specific-user',
            skip=0,
            limit=100
        )

        # Verify aggregation pipeline includes user_id filter
        call_args = mock_collection.aggregate.call_args[0][0]
        self.assertTrue(any('$match' in stage for stage in call_args))
        match_stage = next(stage for stage in call_args if '$match' in stage)
        self.assertEqual(match_stage['$match']['user_id'], 'specific-user')

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabulary_counts_with_pagination(self, mock_get_client):
        """Test vocabulary counts with pagination parameters."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        mock_get_client.return_value = mock_client
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.aggregate.return_value = []

        result = get_vocabulary_counts(
            language=None,
            user_id=self.user_id,
            skip=10,
            limit=50
        )

        # Verify aggregation pipeline includes skip and limit
        call_args = mock_collection.aggregate.call_args[0][0]
        skip_stage = next((stage for stage in call_args if '$skip' in stage), None)
        limit_stage = next((stage for stage in call_args if '$limit' in stage), None)

        self.assertIsNotNone(skip_stage)
        self.assertIsNotNone(limit_stage)
        self.assertEqual(skip_stage['$skip'], 10)
        self.assertEqual(limit_stage['$limit'], 50)

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabulary_counts_skip_zero(self, mock_get_client):
        """Test that skip=0 doesn't add $skip stage."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        mock_get_client.return_value = mock_client
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.aggregate.return_value = []

        result = get_vocabulary_counts(
            language=None,
            user_id=self.user_id,
            skip=0,
            limit=100
        )

        # Verify no $skip stage when skip=0
        call_args = mock_collection.aggregate.call_args[0][0]
        skip_stage = next((stage for stage in call_args if '$skip' in stage), None)
        self.assertIsNone(skip_stage)

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabulary_counts_no_filters(self, mock_get_client):
        """Test vocabulary counts without any filters."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        mock_get_client.return_value = mock_client
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.aggregate.return_value = self.sample_vocab_data

        result = get_vocabulary_counts(
            language=None,
            user_id=None,
            skip=0,
            limit=100
        )

        # Should still return results
        self.assertEqual(len(result), 2)

        # Verify no $match stage when no filters
        call_args = mock_collection.aggregate.call_args[0][0]
        match_stage = next((stage for stage in call_args if '$match' in stage), None)
        # $match might not be present if no conditions
        if match_stage:
            self.assertEqual(match_stage.get('$match'), {})

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabulary_counts_mongodb_unavailable(self, mock_get_client):
        """Test that empty list is returned when MongoDB is unavailable."""
        mock_get_client.return_value = None

        result = get_vocabulary_counts(
            language='English',
            user_id=self.user_id,
            skip=0,
            limit=100
        )

        self.assertEqual(result, [])

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabulary_counts_aggregation_error(self, mock_get_client):
        """Test handling of MongoDB aggregation errors."""
        from pymongo.errors import PyMongoError

        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        mock_get_client.return_value = mock_client
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.aggregate.side_effect = PyMongoError("Aggregation failed")

        result = get_vocabulary_counts(
            language='English',
            user_id=self.user_id,
            skip=0,
            limit=100
        )

        self.assertEqual(result, [])

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabulary_counts_sorting_by_count_and_lemma(self, mock_get_client):
        """Test that results are sorted by count (descending) then lemma (ascending)."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        mock_get_client.return_value = mock_client
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.aggregate.return_value = []

        result = get_vocabulary_counts(
            language=None,
            user_id=self.user_id,
            skip=0,
            limit=100
        )

        # Verify sort stage in pipeline
        call_args = mock_collection.aggregate.call_args[0][0]
        sort_stages = [stage for stage in call_args if '$sort' in stage]
        # Should have sorting stage
        self.assertTrue(len(sort_stages) > 0)
        # Find the sort stage after grouping
        group_idx = next(i for i, stage in enumerate(call_args) if '$group' in stage)
        sort_after_group = next((stage for stage in call_args[group_idx:] if '$sort' in stage), None)
        self.assertIsNotNone(sort_after_group)

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabulary_counts_groups_by_language_and_lemma(self, mock_get_client):
        """Test that aggregation groups by language and lemma."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        mock_get_client.return_value = mock_client
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.aggregate.return_value = []

        result = get_vocabulary_counts(
            language=None,
            user_id=self.user_id,
            skip=0,
            limit=100
        )

        # Verify $group stage
        call_args = mock_collection.aggregate.call_args[0][0]
        group_stage = next(stage for stage in call_args if '$group' in stage)
        self.assertIsNotNone(group_stage)
        group_id = group_stage['$group']['_id']
        self.assertIn('language', group_id)
        self.assertIn('lemma', group_id)

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabulary_counts_returns_most_recent_fields(self, mock_get_client):
        """Test that grouped results include fields from most recent vocabulary."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()

        mock_get_client.return_value = mock_client
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.aggregate.return_value = self.sample_vocab_data

        result = get_vocabulary_counts(
            language='English',
            user_id=self.user_id,
            skip=0,
            limit=100
        )

        # Verify result includes fields from most recent entry
        self.assertIn('definition', result[0])
        self.assertIn('sentence', result[0])
        self.assertIn('word', result[0])
        self.assertIn('created_at', result[0])
        self.assertIn('related_words', result[0])
        self.assertIn('span_id', result[0])


if __name__ == '__main__':
    unittest.main()
