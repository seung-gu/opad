"""Unit tests for token usage tracking functionality.

Tests for:
- save_token_usage() function with various inputs
- TokenUsageRecord database persistence
- Edge cases for token tracking
- Error handling in token usage storage
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from pymongo.errors import PyMongoError

from utils.mongodb import save_token_usage


class TestSaveTokenUsage(unittest.TestCase):
    """Test cases for save_token_usage function."""

    def setUp(self):
        """Set up test fixtures."""
        self.user_id = "test-user-123"
        self.operation = "dictionary_search"
        self.model = "gpt-4.1-mini"
        self.prompt_tokens = 100
        self.completion_tokens = 50
        self.estimated_cost = 0.0001

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_success(self, mock_get_client):
        """Test successful token usage save."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']
        mock_collection.insert_one.return_value = None

        result = save_token_usage(
            user_id=self.user_id,
            operation=self.operation,
            model=self.model,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            estimated_cost=self.estimated_cost
        )

        assert result is not None
        assert isinstance(result, str)
        mock_collection.insert_one.assert_called_once()

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_with_article_id(self, mock_get_client):
        """Test saving token usage with associated article_id."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']
        mock_collection.insert_one.return_value = None

        result = save_token_usage(
            user_id=self.user_id,
            operation=self.operation,
            model=self.model,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            estimated_cost=self.estimated_cost,
            article_id="article-456"
        )

        assert result is not None

        # Verify insert_one was called with article_id
        insert_calls = mock_collection.insert_one.call_args_list
        if insert_calls:
            inserted_doc = insert_calls[0][0][0]
            assert inserted_doc['article_id'] == "article-456"

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_with_metadata(self, mock_get_client):
        """Test saving token usage with metadata."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']
        mock_collection.insert_one.return_value = None

        metadata = {"word": "test", "language": "English"}

        result = save_token_usage(
            user_id=self.user_id,
            operation=self.operation,
            model=self.model,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            estimated_cost=self.estimated_cost,
            metadata=metadata
        )

        assert result is not None

        # Verify metadata was saved
        insert_calls = mock_collection.insert_one.call_args_list
        if insert_calls:
            inserted_doc = insert_calls[0][0][0]
            assert inserted_doc['metadata'] == metadata

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_with_all_parameters(self, mock_get_client):
        """Test saving token usage with all parameters."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']
        mock_collection.insert_one.return_value = None

        metadata = {"word": "test", "language": "English", "pos": "noun"}

        result = save_token_usage(
            user_id=self.user_id,
            operation="article_generation",
            model="gpt-4",
            prompt_tokens=2000,
            completion_tokens=1500,
            estimated_cost=0.0525,
            article_id="article-789",
            metadata=metadata
        )

        assert result is not None

        insert_calls = mock_collection.insert_one.call_args_list
        if insert_calls:
            inserted_doc = insert_calls[0][0][0]
            assert inserted_doc['user_id'] == self.user_id
            assert inserted_doc['operation'] == "article_generation"
            assert inserted_doc['model'] == "gpt-4"
            assert inserted_doc['prompt_tokens'] == 2000
            assert inserted_doc['completion_tokens'] == 1500
            assert inserted_doc['estimated_cost'] == 0.0525
            assert inserted_doc['article_id'] == "article-789"
            assert inserted_doc['metadata'] == metadata

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_creates_document_with_correct_structure(self, mock_get_client):
        """Test that saved document has correct structure."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']
        mock_collection.insert_one.return_value = None

        result = save_token_usage(
            user_id=self.user_id,
            operation=self.operation,
            model=self.model,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            estimated_cost=self.estimated_cost
        )

        assert result is not None

        insert_calls = mock_collection.insert_one.call_args_list
        if insert_calls:
            inserted_doc = insert_calls[0][0][0]

            # Verify document has all required fields
            assert '_id' in inserted_doc
            assert 'user_id' in inserted_doc
            assert 'operation' in inserted_doc
            assert 'model' in inserted_doc
            assert 'prompt_tokens' in inserted_doc
            assert 'completion_tokens' in inserted_doc
            assert 'total_tokens' in inserted_doc
            assert 'estimated_cost' in inserted_doc
            assert 'metadata' in inserted_doc
            assert 'created_at' in inserted_doc

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_calculates_total_tokens(self, mock_get_client):
        """Test that total_tokens is correctly calculated."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']
        mock_collection.insert_one.return_value = None

        result = save_token_usage(
            user_id=self.user_id,
            operation=self.operation,
            model=self.model,
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost=self.estimated_cost
        )

        assert result is not None

        insert_calls = mock_collection.insert_one.call_args_list
        if insert_calls:
            inserted_doc = insert_calls[0][0][0]
            # total_tokens should be sum of prompt and completion
            assert inserted_doc['total_tokens'] == 150

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_with_zero_tokens(self, mock_get_client):
        """Test saving token usage with zero tokens."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']
        mock_collection.insert_one.return_value = None

        result = save_token_usage(
            user_id=self.user_id,
            operation=self.operation,
            model=self.model,
            prompt_tokens=0,
            completion_tokens=0,
            estimated_cost=0.0
        )

        assert result is not None

        insert_calls = mock_collection.insert_one.call_args_list
        if insert_calls:
            inserted_doc = insert_calls[0][0][0]
            assert inserted_doc['total_tokens'] == 0
            assert inserted_doc['estimated_cost'] == 0.0

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_with_large_token_counts(self, mock_get_client):
        """Test saving token usage with very large token counts."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']
        mock_collection.insert_one.return_value = None

        result = save_token_usage(
            user_id=self.user_id,
            operation="article_generation",
            model="gpt-4",
            prompt_tokens=1000000,
            completion_tokens=500000,
            estimated_cost=45.50
        )

        assert result is not None

        insert_calls = mock_collection.insert_one.call_args_list
        if insert_calls:
            inserted_doc = insert_calls[0][0][0]
            assert inserted_doc['prompt_tokens'] == 1000000
            assert inserted_doc['completion_tokens'] == 500000
            assert inserted_doc['total_tokens'] == 1500000
            assert inserted_doc['estimated_cost'] == 45.50

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_with_very_small_cost(self, mock_get_client):
        """Test saving token usage with very small cost."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']
        mock_collection.insert_one.return_value = None

        result = save_token_usage(
            user_id=self.user_id,
            operation=self.operation,
            model=self.model,
            prompt_tokens=1,
            completion_tokens=1,
            estimated_cost=0.00000001
        )

        assert result is not None

        insert_calls = mock_collection.insert_one.call_args_list
        if insert_calls:
            inserted_doc = insert_calls[0][0][0]
            assert inserted_doc['estimated_cost'] == 0.00000001

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_returns_none_on_invalid_user_id_empty(self, mock_get_client):
        """Test that empty user_id returns None."""
        result = save_token_usage(
            user_id="",
            operation=self.operation,
            model=self.model,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            estimated_cost=self.estimated_cost
        )

        assert result is None
        mock_get_client.assert_not_called()

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_returns_none_on_invalid_user_id_whitespace(self, mock_get_client):
        """Test that whitespace-only user_id returns None."""
        result = save_token_usage(
            user_id="   ",
            operation=self.operation,
            model=self.model,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            estimated_cost=self.estimated_cost
        )

        assert result is None
        mock_get_client.assert_not_called()

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_returns_none_on_invalid_user_id_none(self, mock_get_client):
        """Test that None user_id returns None."""
        result = save_token_usage(
            user_id=None,
            operation=self.operation,
            model=self.model,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            estimated_cost=self.estimated_cost
        )

        assert result is None

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_returns_none_on_no_mongodb_connection(self, mock_get_client):
        """Test that None is returned when MongoDB connection fails."""
        mock_get_client.return_value = None

        result = save_token_usage(
            user_id=self.user_id,
            operation=self.operation,
            model=self.model,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            estimated_cost=self.estimated_cost
        )

        assert result is None

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_handles_pymongo_error(self, mock_get_client):
        """Test graceful handling of PyMongoError."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']
        mock_collection.insert_one.side_effect = PyMongoError("Database error")

        result = save_token_usage(
            user_id=self.user_id,
            operation=self.operation,
            model=self.model,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            estimated_cost=self.estimated_cost
        )

        assert result is None

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_with_different_operations(self, mock_get_client):
        """Test saving token usage for different operation types."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']
        mock_collection.insert_one.return_value = None

        operations = ["dictionary_search", "article_generation"]

        for operation in operations:
            mock_collection.reset_mock()

            result = save_token_usage(
                user_id=self.user_id,
                operation=operation,
                model=self.model,
                prompt_tokens=self.prompt_tokens,
                completion_tokens=self.completion_tokens,
                estimated_cost=self.estimated_cost
            )

            assert result is not None

            insert_calls = mock_collection.insert_one.call_args_list
            if insert_calls:
                inserted_doc = insert_calls[0][0][0]
                assert inserted_doc['operation'] == operation

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_with_different_models(self, mock_get_client):
        """Test saving token usage for different model names."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']
        mock_collection.insert_one.return_value = None

        models = ["gpt-4.1-mini", "gpt-4", "claude-3-opus", "claude-3-sonnet"]

        for model in models:
            mock_collection.reset_mock()

            result = save_token_usage(
                user_id=self.user_id,
                operation=self.operation,
                model=model,
                prompt_tokens=self.prompt_tokens,
                completion_tokens=self.completion_tokens,
                estimated_cost=self.estimated_cost
            )

            assert result is not None

            insert_calls = mock_collection.insert_one.call_args_list
            if insert_calls:
                inserted_doc = insert_calls[0][0][0]
                assert inserted_doc['model'] == model

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_sets_created_at_timestamp(self, mock_get_client):
        """Test that created_at timestamp is set."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']
        mock_collection.insert_one.return_value = None

        before_call = datetime.now(timezone.utc)

        result = save_token_usage(
            user_id=self.user_id,
            operation=self.operation,
            model=self.model,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            estimated_cost=self.estimated_cost
        )

        after_call = datetime.now(timezone.utc)

        assert result is not None

        insert_calls = mock_collection.insert_one.call_args_list
        if insert_calls:
            inserted_doc = insert_calls[0][0][0]
            assert 'created_at' in inserted_doc
            created_at = inserted_doc['created_at']
            assert before_call <= created_at <= after_call

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_with_empty_metadata_dict(self, mock_get_client):
        """Test saving token usage with empty metadata."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']
        mock_collection.insert_one.return_value = None

        result = save_token_usage(
            user_id=self.user_id,
            operation=self.operation,
            model=self.model,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            estimated_cost=self.estimated_cost,
            metadata={}
        )

        assert result is not None

        insert_calls = mock_collection.insert_one.call_args_list
        if insert_calls:
            inserted_doc = insert_calls[0][0][0]
            assert inserted_doc['metadata'] == {}

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_with_complex_metadata(self, mock_get_client):
        """Test saving token usage with nested metadata."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']
        mock_collection.insert_one.return_value = None

        complex_metadata = {
            "word": "test",
            "language": "English",
            "context": {
                "lemma": "test",
                "pos": "noun",
                "level": "B1"
            },
            "tags": ["vocabulary", "search", "test"]
        }

        result = save_token_usage(
            user_id=self.user_id,
            operation=self.operation,
            model=self.model,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            estimated_cost=self.estimated_cost,
            metadata=complex_metadata
        )

        assert result is not None

        insert_calls = mock_collection.insert_one.call_args_list
        if insert_calls:
            inserted_doc = insert_calls[0][0][0]
            assert inserted_doc['metadata'] == complex_metadata
            assert inserted_doc['metadata']['context']['pos'] == "noun"


class TestSaveTokenUsageIntegration(unittest.TestCase):
    """Integration tests for token usage tracking."""

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_multiple_token_usages_for_same_user(self, mock_get_client):
        """Test saving multiple token usage records for the same user."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']
        mock_collection.insert_one.return_value = None

        user_id = "user-123"

        # Save first usage
        result1 = save_token_usage(
            user_id=user_id,
            operation="dictionary_search",
            model="gpt-4.1-mini",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost=0.0001,
            metadata={"word": "test"}
        )

        # Save second usage
        result2 = save_token_usage(
            user_id=user_id,
            operation="article_generation",
            model="gpt-4",
            prompt_tokens=2000,
            completion_tokens=1500,
            estimated_cost=0.0525,
            metadata={"article_id": "article-123"}
        )

        assert result1 is not None
        assert result2 is not None

        # Verify both were saved
        assert mock_collection.insert_one.call_count == 2

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_token_usage_for_article_workflow(self, mock_get_client):
        """Test typical token usage workflow for article generation."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['token_usage']
        mock_collection.insert_one.return_value = None

        user_id = "user-123"
        article_id = "article-456"

        # User searches for vocabulary while reading
        result1 = save_token_usage(
            user_id=user_id,
            operation="dictionary_search",
            model="gpt-4.1-mini",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost=0.0001,
            article_id=article_id,
            metadata={"word": "gehen", "language": "German"}
        )

        # Article generation uses tokens
        result2 = save_token_usage(
            user_id=user_id,
            operation="article_generation",
            model="gpt-4",
            prompt_tokens=2500,
            completion_tokens=2000,
            estimated_cost=0.0675,
            article_id=article_id,
            metadata={"topic": "technology", "language": "German"}
        )

        assert result1 is not None
        assert result2 is not None

        # Both should be associated with the same article
        insert_calls = mock_collection.insert_one.call_args_list
        assert len(insert_calls) == 2
        assert insert_calls[0][0][0]['article_id'] == article_id
        assert insert_calls[1][0][0]['article_id'] == article_id


if __name__ == '__main__':
    unittest.main()
