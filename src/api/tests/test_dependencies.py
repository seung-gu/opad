"""Unit tests for API dependencies — get_article_repo() dependency injection.

Tests focus on the wiring logic inside get_article_repo():
- 503 when MongoDB client is None
- Correct database name is used
- MongoArticleRepository receives the database instance
- Returned repository exposes all ArticleRepository protocol methods
"""

import unittest
from unittest.mock import patch, MagicMock

from fastapi import HTTPException

from api.dependencies import get_article_repo
from adapter.mongodb.article_repository import MongoArticleRepository


class TestGetArticleRepo(unittest.TestCase):
    """Test cases for get_article_repo() dependency injection function."""

    @patch('api.dependencies.get_mongodb_client')
    def test_returns_mongo_repository_when_connected(self, mock_get_client):
        """get_article_repo() returns MongoArticleRepository when MongoDB is connected."""
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = MagicMock()
        mock_get_client.return_value = mock_client

        repo = get_article_repo()

        self.assertIsInstance(repo, MongoArticleRepository)
        mock_get_client.assert_called_once()

    @patch('api.dependencies.get_mongodb_client')
    def test_raises_503_when_mongodb_unavailable(self, mock_get_client):
        """get_article_repo() raises 503 HTTPException when MongoDB client is None."""
        mock_get_client.return_value = None

        with self.assertRaises(HTTPException) as context:
            get_article_repo()

        self.assertEqual(context.exception.status_code, 503)
        self.assertEqual(context.exception.detail, "Database unavailable")

    @patch('api.dependencies.get_mongodb_client')
    def test_uses_correct_database_name(self, mock_get_client):
        """get_article_repo() accesses the database using DATABASE_NAME."""
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = MagicMock()
        mock_get_client.return_value = mock_client

        get_article_repo()

        from api.dependencies import DATABASE_NAME
        mock_client.__getitem__.assert_called_with(DATABASE_NAME)

    @patch('api.dependencies.get_mongodb_client')
    def test_passes_db_to_mongo_repository(self, mock_get_client):
        """get_article_repo() passes the database instance to MongoArticleRepository."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_get_client.return_value = mock_client

        with patch('api.dependencies.MongoArticleRepository') as mock_repo_class:
            mock_repo_class.return_value = MagicMock()
            get_article_repo()
            mock_repo_class.assert_called_once_with(mock_db)

    @patch('api.dependencies.get_mongodb_client')
    def test_returns_protocol_compatible_object(self, mock_get_client):
        """get_article_repo() returns object with all ArticleRepository protocol methods."""
        mock_client = MagicMock()
        mock_client.__getitem__.return_value = MagicMock()
        mock_get_client.return_value = mock_client

        repo = get_article_repo()

        expected_methods = [
            'save_metadata', 'save_content', 'get_by_id',
            'find_many', 'find_duplicate', 'update_status', 'delete',
        ]
        for method in expected_methods:
            self.assertTrue(
                hasattr(repo, method),
                f"MongoArticleRepository missing protocol method: {method}"
            )


if __name__ == '__main__':
    unittest.main()
