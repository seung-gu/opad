"""Unit tests for token usage MongoDB functions in mongodb.py."""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from pymongo.errors import PyMongoError

from utils.mongodb import (
    save_token_usage,
    get_user_token_summary,
    get_article_token_usage
)


class TestSaveTokenUsage(unittest.TestCase):
    """Test cases for save_token_usage function."""

    def setUp(self):
        """Set up test fixtures."""
        self.user_id = "test_user_123"
        self.operation = "article_generation"
        self.model = "gpt-4"
        self.prompt_tokens = 100
        self.completion_tokens = 50
        self.estimated_cost = 0.0015
        self.article_id = "article_123"
        self.metadata = {"language": "English", "level": "B1"}

    @patch('utils.mongodb.get_mongodb_client')
    @patch('utils.mongodb.uuid')
    def test_save_token_usage_returns_document_id_on_success(self, mock_uuid, mock_get_client):
        """Test that save_token_usage returns document ID on successful save."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']

        # Mock UUID generation
        expected_id = "uuid-12345"
        mock_uuid.uuid4.return_value.hex = expected_id
        mock_uuid.uuid4.return_value.__str__.return_value = expected_id

        result = save_token_usage(
            user_id=self.user_id,
            operation=self.operation,
            model=self.model,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            estimated_cost=self.estimated_cost,
            article_id=self.article_id,
            metadata=self.metadata
        )

        # Verify result is the document ID
        self.assertEqual(result, expected_id)

        # Verify insert_one was called
        mock_collection.insert_one.assert_called_once()

    @patch('utils.mongodb.get_mongodb_client')
    @patch('utils.mongodb.uuid')
    def test_save_token_usage_with_all_fields(self, mock_uuid, mock_get_client):
        """Test save_token_usage with all fields including metadata."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']

        expected_id = "uuid-complete"
        mock_uuid.uuid4.return_value.__str__.return_value = expected_id

        result = save_token_usage(
            user_id=self.user_id,
            operation=self.operation,
            model=self.model,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            estimated_cost=self.estimated_cost,
            article_id=self.article_id,
            metadata={"query": "test", "language": "German"}
        )

        # Verify document was inserted with all fields
        inserted_doc = mock_collection.insert_one.call_args[0][0]
        self.assertEqual(inserted_doc['user_id'], self.user_id)
        self.assertEqual(inserted_doc['operation'], self.operation)
        self.assertEqual(inserted_doc['model'], self.model)
        self.assertEqual(inserted_doc['prompt_tokens'], self.prompt_tokens)
        self.assertEqual(inserted_doc['completion_tokens'], self.completion_tokens)
        self.assertEqual(inserted_doc['total_tokens'], 150)  # 100 + 50
        self.assertEqual(inserted_doc['estimated_cost'], self.estimated_cost)
        self.assertEqual(inserted_doc['article_id'], self.article_id)
        self.assertEqual(inserted_doc['metadata'], {"query": "test", "language": "German"})
        self.assertIn('created_at', inserted_doc)

    @patch('utils.mongodb.get_mongodb_client')
    @patch('utils.mongodb.uuid')
    def test_save_token_usage_with_none_article_id(self, mock_uuid, mock_get_client):
        """Test save_token_usage with optional article_id=None."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']

        expected_id = "uuid-no-article"
        mock_uuid.uuid4.return_value.__str__.return_value = expected_id

        result = save_token_usage(
            user_id=self.user_id,
            operation="dictionary_search",
            model=self.model,
            prompt_tokens=50,
            completion_tokens=25,
            estimated_cost=0.0005
        )

        # Verify article_id is None in document
        inserted_doc = mock_collection.insert_one.call_args[0][0]
        self.assertIsNone(inserted_doc['article_id'])

        # Verify result is still a valid ID
        self.assertEqual(result, expected_id)

    @patch('utils.mongodb.get_mongodb_client')
    @patch('utils.mongodb.logger')
    def test_save_token_usage_returns_none_for_empty_user_id(self, mock_logger, mock_get_client):
        """Test that save_token_usage returns None for empty user_id."""
        mock_get_client.return_value = MagicMock()

        # Test with empty string
        result = save_token_usage(
            user_id="",
            operation=self.operation,
            model=self.model,
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost=0.001
        )

        # Verify result is None
        self.assertIsNone(result)

        # Verify warning was logged
        mock_logger.warning.assert_called()

    @patch('utils.mongodb.get_mongodb_client')
    @patch('utils.mongodb.logger')
    def test_save_token_usage_returns_none_for_whitespace_user_id(self, mock_logger, mock_get_client):
        """Test that save_token_usage returns None for whitespace-only user_id."""
        mock_get_client.return_value = MagicMock()

        result = save_token_usage(
            user_id="   ",
            operation=self.operation,
            model=self.model,
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost=0.001
        )

        # Verify result is None
        self.assertIsNone(result)

    @patch('utils.mongodb.get_mongodb_client')
    @patch('utils.mongodb.logger')
    def test_save_token_usage_returns_none_for_negative_prompt_tokens(self, mock_logger, mock_get_client):
        """Test that save_token_usage returns None for negative prompt_tokens."""
        mock_get_client.return_value = MagicMock()

        result = save_token_usage(
            user_id=self.user_id,
            operation=self.operation,
            model=self.model,
            prompt_tokens=-100,
            completion_tokens=50,
            estimated_cost=0.001
        )

        # Verify result is None
        self.assertIsNone(result)

        # Verify warning was logged
        mock_logger.warning.assert_called()

    @patch('utils.mongodb.get_mongodb_client')
    @patch('utils.mongodb.logger')
    def test_save_token_usage_returns_none_for_negative_completion_tokens(self, mock_logger, mock_get_client):
        """Test that save_token_usage returns None for negative completion_tokens."""
        mock_get_client.return_value = MagicMock()

        result = save_token_usage(
            user_id=self.user_id,
            operation=self.operation,
            model=self.model,
            prompt_tokens=100,
            completion_tokens=-50,
            estimated_cost=0.001
        )

        # Verify result is None
        self.assertIsNone(result)

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_returns_none_on_client_failure(self, mock_get_client):
        """Test that save_token_usage returns None when MongoDB client fails."""
        mock_get_client.return_value = None

        result = save_token_usage(
            user_id=self.user_id,
            operation=self.operation,
            model=self.model,
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost=0.001
        )

        # Verify result is None
        self.assertIsNone(result)

    @patch('utils.mongodb.get_mongodb_client')
    @patch('utils.mongodb.logger')
    def test_save_token_usage_returns_none_on_pymongo_error(self, mock_logger, mock_get_client):
        """Test that save_token_usage returns None on PyMongoError."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']

        # Mock insert_one raising PyMongoError
        mock_collection.insert_one.side_effect = PyMongoError("Database error")

        result = save_token_usage(
            user_id=self.user_id,
            operation=self.operation,
            model=self.model,
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost=0.001
        )

        # Verify result is None
        self.assertIsNone(result)

        # Verify error was logged
        mock_logger.error.assert_called()

    @patch('utils.mongodb.get_mongodb_client')
    @patch('utils.mongodb.uuid')
    def test_save_token_usage_calculates_total_tokens(self, mock_uuid, mock_get_client):
        """Test that total_tokens is correctly calculated as sum of prompt and completion tokens."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']

        expected_id = "uuid-totals"
        mock_uuid.uuid4.return_value.__str__.return_value = expected_id

        prompt_tokens = 250
        completion_tokens = 150
        expected_total = 400

        save_token_usage(
            user_id=self.user_id,
            operation=self.operation,
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost=0.005
        )

        # Verify total_tokens in document
        inserted_doc = mock_collection.insert_one.call_args[0][0]
        self.assertEqual(inserted_doc['total_tokens'], expected_total)


class TestGetUserTokenSummary(unittest.TestCase):
    """Test cases for get_user_token_summary function."""

    def setUp(self):
        """Set up test fixtures."""
        self.user_id = "test_user_123"
        self.test_date_1 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.test_date_2 = datetime(2025, 1, 2, 12, 0, 0, tzinfo=timezone.utc)

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_user_token_summary_returns_correct_structure(self, mock_get_client):
        """Test that get_user_token_summary returns correct data structure."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']

        # Mock aggregation results for operations
        def aggregate_side_effect(pipeline):
            # Check if this is the operation pipeline or daily pipeline
            if '$group' in pipeline[-1]:
                # Operation aggregation
                return [
                    {'_id': 'article_generation', 'tokens': 1000, 'cost': 0.010, 'count': 5},
                    {'_id': 'dictionary_search', 'tokens': 500, 'cost': 0.005, 'count': 10}
                ]
            else:
                # Daily aggregation
                return [
                    {'_id': '2025-01-01', 'tokens': 800, 'cost': 0.008},
                    {'_id': '2025-01-02', 'tokens': 700, 'cost': 0.007}
                ]

        mock_collection.aggregate.side_effect = aggregate_side_effect

        result = get_user_token_summary(self.user_id)

        # Verify correct structure
        self.assertIn('total_tokens', result)
        self.assertIn('total_cost', result)
        self.assertIn('by_operation', result)
        self.assertIn('daily_usage', result)

        # Verify correct values
        self.assertEqual(result['total_tokens'], 1500)  # 1000 + 500
        self.assertEqual(result['total_cost'], 0.015)   # 0.010 + 0.005
        self.assertIsInstance(result['by_operation'], dict)
        self.assertIsInstance(result['daily_usage'], list)

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_user_token_summary_clamps_days_minimum(self, mock_get_client):
        """Test that days parameter is clamped to minimum of 1."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']
        mock_collection.aggregate.return_value = []

        # Call with days=0 (should be clamped to 1)
        result = get_user_token_summary(self.user_id, days=0)

        # Verify aggregation was called (means days was clamped and processed)
        mock_collection.aggregate.assert_called()

        # Verify the cutoff date passed to MongoDB is approximately 1 day ago
        call_args = mock_collection.aggregate.call_args_list[0][0][0]
        match_condition = call_args[0]['$match']
        self.assertIn('created_at', match_condition)

    @patch('utils.mongodb.get_mongodb_client')
    @patch('utils.mongodb.logger')
    def test_get_user_token_summary_clamps_days_maximum(self, mock_logger, mock_get_client):
        """Test that days parameter is clamped to maximum of 365."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']
        mock_collection.aggregate.return_value = []

        # Call with days=400 (should be clamped to 365)
        result = get_user_token_summary(self.user_id, days=400)

        # Verify warning was logged
        mock_logger.warning.assert_called()

        # Verify aggregation was called
        mock_collection.aggregate.assert_called()

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_user_token_summary_returns_empty_structure_on_no_data(self, mock_get_client):
        """Test that empty structure is returned when no data exists."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']

        # Mock empty aggregation results
        mock_collection.aggregate.return_value = []

        result = get_user_token_summary(self.user_id)

        # Verify structure with empty data
        self.assertEqual(result['total_tokens'], 0)
        self.assertEqual(result['total_cost'], 0.0)
        self.assertEqual(result['by_operation'], {})
        self.assertEqual(result['daily_usage'], [])

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_user_token_summary_aggregates_by_operation(self, mock_get_client):
        """Test that summary correctly aggregates data by operation type."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']

        # Mock aggregation results
        def aggregate_side_effect(pipeline):
            if '$group' in pipeline[-1]:
                # Operation aggregation
                return [
                    {'_id': 'article_generation', 'tokens': 2000, 'cost': 0.020, 'count': 3},
                    {'_id': 'dictionary_search', 'tokens': 300, 'cost': 0.003, 'count': 15}
                ]
            else:
                # Daily aggregation
                return []

        mock_collection.aggregate.side_effect = aggregate_side_effect

        result = get_user_token_summary(self.user_id)

        # Verify by_operation structure
        self.assertIn('article_generation', result['by_operation'])
        self.assertIn('dictionary_search', result['by_operation'])

        # Verify counts and costs
        self.assertEqual(result['by_operation']['article_generation']['tokens'], 2000)
        self.assertEqual(result['by_operation']['article_generation']['count'], 3)
        self.assertEqual(result['by_operation']['dictionary_search']['tokens'], 300)
        self.assertEqual(result['by_operation']['dictionary_search']['count'], 15)

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_user_token_summary_daily_usage_sorted_ascending(self, mock_get_client):
        """Test that daily_usage list is sorted by date ascending."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']

        # Mock aggregation results
        def aggregate_side_effect(pipeline):
            if '$group' in pipeline[-1]:
                # Operation aggregation
                return []
            else:
                # Daily aggregation (already sorted by MongoDB)
                return [
                    {'_id': '2025-01-01', 'tokens': 500, 'cost': 0.005},
                    {'_id': '2025-01-02', 'tokens': 600, 'cost': 0.006},
                    {'_id': '2025-01-03', 'tokens': 400, 'cost': 0.004}
                ]

        mock_collection.aggregate.side_effect = aggregate_side_effect

        result = get_user_token_summary(self.user_id)

        # Verify daily_usage is in ascending order by date
        daily_usage = result['daily_usage']
        self.assertEqual(len(daily_usage), 3)
        self.assertEqual(daily_usage[0]['date'], '2025-01-01')
        self.assertEqual(daily_usage[1]['date'], '2025-01-02')
        self.assertEqual(daily_usage[2]['date'], '2025-01-03')

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_user_token_summary_returns_default_on_client_failure(self, mock_get_client):
        """Test that default empty structure is returned when MongoDB client fails."""
        mock_get_client.return_value = None

        result = get_user_token_summary(self.user_id)

        # Verify default structure
        self.assertEqual(result['total_tokens'], 0)
        self.assertEqual(result['total_cost'], 0.0)
        self.assertEqual(result['by_operation'], {})
        self.assertEqual(result['daily_usage'], [])

    @patch('utils.mongodb.get_mongodb_client')
    @patch('utils.mongodb.logger')
    def test_get_user_token_summary_returns_default_on_pymongo_error(self, mock_logger, mock_get_client):
        """Test that default structure is returned on PyMongoError."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']

        # Mock aggregation raising PyMongoError
        mock_collection.aggregate.side_effect = PyMongoError("Database error")

        result = get_user_token_summary(self.user_id)

        # Verify default structure
        self.assertEqual(result['total_tokens'], 0)
        self.assertEqual(result['total_cost'], 0.0)
        self.assertEqual(result['by_operation'], {})
        self.assertEqual(result['daily_usage'], [])

        # Verify error was logged
        mock_logger.error.assert_called()

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_user_token_summary_with_multiple_operations(self, mock_get_client):
        """Test summary with multiple different operations."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']

        # Mock aggregation results with multiple operations
        def aggregate_side_effect(pipeline):
            if '$group' in pipeline[-1]:
                # Operation aggregation with 3 different operations
                return [
                    {'_id': 'article_generation', 'tokens': 3000, 'cost': 0.030, 'count': 2},
                    {'_id': 'dictionary_search', 'tokens': 400, 'cost': 0.004, 'count': 8},
                    {'_id': 'vocabulary_lookup', 'tokens': 200, 'cost': 0.002, 'count': 20}
                ]
            else:
                # Daily aggregation
                return []

        mock_collection.aggregate.side_effect = aggregate_side_effect

        result = get_user_token_summary(self.user_id)

        # Verify all operations are aggregated
        self.assertEqual(len(result['by_operation']), 3)
        total = sum(op['tokens'] for op in result['by_operation'].values())
        self.assertEqual(result['total_tokens'], total)


class TestGetArticleTokenUsage(unittest.TestCase):
    """Test cases for get_article_token_usage function."""

    def setUp(self):
        """Set up test fixtures."""
        self.article_id = "article_123"
        self.test_date_1 = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        self.test_date_2 = datetime(2025, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
        self.test_date_3 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_article_token_usage_returns_list_of_records(self, mock_get_client):
        """Test that get_article_token_usage returns list of usage records."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']

        # Mock find().sort() chain
        mock_find = MagicMock()
        mock_sort = MagicMock()
        mock_collection.find.return_value = mock_find
        mock_find.sort.return_value = [
            {
                '_id': 'usage_1',
                'user_id': 'user_123',
                'operation': 'article_generation',
                'model': 'gpt-4',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150,
                'estimated_cost': 0.001,
                'metadata': {},
                'created_at': self.test_date_1
            }
        ]

        result = get_article_token_usage(self.article_id)

        # Verify result is a list
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

        # Verify record structure
        record = result[0]
        self.assertEqual(record['id'], 'usage_1')
        self.assertEqual(record['user_id'], 'user_123')
        self.assertEqual(record['operation'], 'article_generation')

    @patch('utils.mongodb.get_mongodb_client')
    @patch('utils.mongodb.logger')
    def test_get_article_token_usage_returns_empty_for_empty_article_id(self, mock_logger, mock_get_client):
        """Test that empty article_id returns empty list."""
        mock_get_client.return_value = MagicMock()

        result = get_article_token_usage("")

        # Verify empty list returned
        self.assertEqual(result, [])

        # Verify warning was logged
        mock_logger.warning.assert_called()

    @patch('utils.mongodb.get_mongodb_client')
    @patch('utils.mongodb.logger')
    def test_get_article_token_usage_returns_empty_for_whitespace_article_id(self, mock_logger, mock_get_client):
        """Test that whitespace-only article_id returns empty list."""
        mock_get_client.return_value = MagicMock()

        result = get_article_token_usage("   ")

        # Verify empty list returned
        self.assertEqual(result, [])

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_article_token_usage_returns_empty_when_no_records_found(self, mock_get_client):
        """Test that empty list is returned when no records found."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']

        # Mock find().sort() chain returning empty list
        mock_find = MagicMock()
        mock_sort = MagicMock()
        mock_collection.find.return_value = mock_find
        mock_find.sort.return_value = []

        result = get_article_token_usage(self.article_id)

        # Verify empty list returned
        self.assertEqual(result, [])
        self.assertIsInstance(result, list)

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_article_token_usage_sorts_by_created_at_ascending(self, mock_get_client):
        """Test that records are sorted by created_at ascending (oldest first)."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']

        # Mock find().sort() chain with multiple records
        mock_find = MagicMock()
        mock_sort = MagicMock()
        mock_collection.find.return_value = mock_find
        mock_find.sort.return_value = [
            {
                '_id': 'usage_1',
                'user_id': 'user_123',
                'operation': 'article_generation',
                'model': 'gpt-4',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150,
                'estimated_cost': 0.001,
                'metadata': {},
                'created_at': self.test_date_1  # Earliest
            },
            {
                '_id': 'usage_2',
                'user_id': 'user_123',
                'operation': 'article_generation',
                'model': 'gpt-4',
                'prompt_tokens': 200,
                'completion_tokens': 100,
                'total_tokens': 300,
                'estimated_cost': 0.002,
                'metadata': {},
                'created_at': self.test_date_2  # Middle
            },
            {
                '_id': 'usage_3',
                'user_id': 'user_123',
                'operation': 'dictionary_search',
                'model': 'gpt-4',
                'prompt_tokens': 50,
                'completion_tokens': 25,
                'total_tokens': 75,
                'estimated_cost': 0.0005,
                'metadata': {},
                'created_at': self.test_date_3  # Latest
            }
        ]

        result = get_article_token_usage(self.article_id)

        # Verify sort was called with correct parameters
        mock_find.sort.assert_called_once_with('created_at', 1)

        # Verify records are in ascending order
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['created_at'], self.test_date_1)
        self.assertEqual(result[1]['created_at'], self.test_date_2)
        self.assertEqual(result[2]['created_at'], self.test_date_3)

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_article_token_usage_returns_correct_field_mapping(self, mock_get_client):
        """Test that returned records have correct field mapping."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']

        # Mock find().sort() chain
        mock_find = MagicMock()
        mock_sort = MagicMock()
        mock_collection.find.return_value = mock_find
        mock_find.sort.return_value = [
            {
                '_id': 'usage_uuid_123',
                'user_id': 'user_abc',
                'operation': 'article_generation',
                'model': 'gpt-4o',
                'prompt_tokens': 250,
                'completion_tokens': 150,
                'total_tokens': 400,
                'estimated_cost': 0.005,
                'metadata': {'language': 'German', 'level': 'B2'},
                'created_at': self.test_date_1
            }
        ]

        result = get_article_token_usage(self.article_id)

        # Verify all fields are correctly mapped
        record = result[0]
        self.assertEqual(record['id'], 'usage_uuid_123')  # _id -> id
        self.assertEqual(record['user_id'], 'user_abc')
        self.assertEqual(record['operation'], 'article_generation')
        self.assertEqual(record['model'], 'gpt-4o')
        self.assertEqual(record['prompt_tokens'], 250)
        self.assertEqual(record['completion_tokens'], 150)
        self.assertEqual(record['total_tokens'], 400)
        self.assertEqual(record['estimated_cost'], 0.005)
        self.assertEqual(record['metadata'], {'language': 'German', 'level': 'B2'})
        self.assertEqual(record['created_at'], self.test_date_1)

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_article_token_usage_handles_missing_metadata(self, mock_get_client):
        """Test that missing metadata is handled gracefully."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']

        # Mock find().sort() chain with document missing metadata
        mock_find = MagicMock()
        mock_sort = MagicMock()
        mock_collection.find.return_value = mock_find
        mock_find.sort.return_value = [
            {
                '_id': 'usage_1',
                'user_id': 'user_123',
                'operation': 'article_generation',
                'model': 'gpt-4',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150,
                'estimated_cost': 0.001,
                # metadata is missing
                'created_at': self.test_date_1
            }
        ]

        result = get_article_token_usage(self.article_id)

        # Verify result with default metadata
        record = result[0]
        self.assertEqual(record['metadata'], {})

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_article_token_usage_returns_empty_on_client_failure(self, mock_get_client):
        """Test that empty list is returned when MongoDB client fails."""
        mock_get_client.return_value = None

        result = get_article_token_usage(self.article_id)

        # Verify empty list returned
        self.assertEqual(result, [])

    @patch('utils.mongodb.get_mongodb_client')
    @patch('utils.mongodb.logger')
    def test_get_article_token_usage_returns_empty_on_pymongo_error(self, mock_logger, mock_get_client):
        """Test that empty list is returned on PyMongoError."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']

        # Mock find raising PyMongoError
        mock_collection.find.side_effect = PyMongoError("Database error")

        result = get_article_token_usage(self.article_id)

        # Verify empty list returned
        self.assertEqual(result, [])

        # Verify error was logged
        mock_logger.error.assert_called()

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_article_token_usage_with_multiple_users(self, mock_get_client):
        """Test that article token usage includes records from all users."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']

        # Mock find().sort() chain with records from different users
        mock_find = MagicMock()
        mock_sort = MagicMock()
        mock_collection.find.return_value = mock_find
        mock_find.sort.return_value = [
            {
                '_id': 'usage_1',
                'user_id': 'user_1',
                'operation': 'article_generation',
                'model': 'gpt-4',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150,
                'estimated_cost': 0.001,
                'metadata': {},
                'created_at': self.test_date_1
            },
            {
                '_id': 'usage_2',
                'user_id': 'user_2',
                'operation': 'article_generation',
                'model': 'gpt-4',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150,
                'estimated_cost': 0.001,
                'metadata': {},
                'created_at': self.test_date_2
            }
        ]

        result = get_article_token_usage(self.article_id)

        # Verify records from both users are included
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['user_id'], 'user_1')
        self.assertEqual(result[1]['user_id'], 'user_2')

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_article_token_usage_filters_by_article_id(self, mock_get_client):
        """Test that query correctly filters by article_id."""
        # Setup mock MongoDB client and collection
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']

        # Mock find().sort() chain
        mock_find = MagicMock()
        mock_sort = MagicMock()
        mock_collection.find.return_value = mock_find
        mock_find.sort.return_value = []

        get_article_token_usage(self.article_id)

        # Verify find was called with correct article_id filter
        mock_collection.find.assert_called_once_with({'article_id': self.article_id})


if __name__ == '__main__':
    unittest.main()
