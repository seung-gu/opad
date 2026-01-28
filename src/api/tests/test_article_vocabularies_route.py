"""Unit tests for article vocabularies route."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from api.main import app
from api.models import User
from api.middleware.auth import get_current_user_required


class TestGetArticleVocabularies(unittest.TestCase):
    """Test cases for GET /articles/{article_id}/vocabularies endpoint."""

    def setUp(self):
        """Set up test client and fixtures."""
        self.client = TestClient(app)
        self.mock_user = User(
            id="test-user-123",
            email="test@example.com",
            name="Test User",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            provider="email"
        )
        self.article_id = "test-article-123"

    def tearDown(self):
        """Clean up dependency overrides."""
        app.dependency_overrides.clear()

    @patch('api.routes.articles.get_vocabularies')
    @patch('api.routes.articles.get_article')
    @patch('api.routes.articles.get_mongodb_client')
    def test_get_article_vocabularies_success(self, mock_client, mock_get_article, mock_get_vocabs):
        """Test successful retrieval of article vocabularies."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_client.return_value = MagicMock()
        mock_get_article.return_value = {
            '_id': self.article_id,
            'user_id': 'test-user-123',
            'inputs': {
                'language': 'English',
                'level': 'B2',
                'length': '500',
                'topic': 'AI'
            },
            'status': 'completed'
        }
        mock_get_vocabs.return_value = [
            {
                'id': 'vocab-1',
                'article_id': self.article_id,
                'word': 'testing',
                'lemma': 'test',
                'definition': 'a procedure',
                'sentence': 'This is a test.',
                'language': 'English',
                'related_words': None,
                'span_id': None,
                'created_at': datetime.now(timezone.utc),
                'user_id': 'test-user-123'
            }
        ]

        response = self.client.get(f"/articles/{self.article_id}/vocabularies")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['lemma'], 'test')
        self.assertEqual(data[0]['article_id'], self.article_id)

        # Verify get_vocabularies was called with correct params
        mock_get_vocabs.assert_called_once_with(
            article_id=self.article_id,
            user_id='test-user-123'
        )

    @patch('api.routes.articles.get_article')
    @patch('api.routes.articles.get_mongodb_client')
    def test_get_article_vocabularies_article_not_found(self, mock_client, mock_get_article):
        """Test 404 response when article doesn't exist."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_client.return_value = MagicMock()
        mock_get_article.return_value = None

        response = self.client.get(f"/articles/{self.article_id}/vocabularies")

        self.assertEqual(response.status_code, 404)
        self.assertIn("Article not found", response.json()['detail'])

    @patch('api.routes.articles.get_article')
    @patch('api.routes.articles.get_mongodb_client')
    def test_get_article_vocabularies_unauthorized_access(self, mock_client, mock_get_article):
        """Test 403 response when user doesn't own the article."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_client.return_value = MagicMock()
        # Article exists but belongs to different user
        mock_get_article.return_value = {
            '_id': self.article_id,
            'user_id': 'different-user-456',
            'inputs': {
                'language': 'English',
                'level': 'B2',
                'length': '500',
                'topic': 'AI'
            },
            'status': 'completed'
        }

        response = self.client.get(f"/articles/{self.article_id}/vocabularies")

        self.assertEqual(response.status_code, 403)
        self.assertIn("don't have permission", response.json()['detail'])

    def test_get_article_vocabularies_requires_authentication(self):
        """Test that endpoint requires authentication."""
        from fastapi import HTTPException

        # Override dependency to raise authentication error
        def mock_auth_fail():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user_required] = mock_auth_fail

        response = self.client.get(f"/articles/{self.article_id}/vocabularies")

        self.assertEqual(response.status_code, 401)

    @patch('api.routes.articles.get_vocabularies')
    @patch('api.routes.articles.get_article')
    @patch('api.routes.articles.get_mongodb_client')
    def test_get_article_vocabularies_empty_result(self, mock_client, mock_get_article, mock_get_vocabs):
        """Test successful response with no vocabularies."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_client.return_value = MagicMock()
        mock_get_article.return_value = {
            '_id': self.article_id,
            'user_id': 'test-user-123',
            'inputs': {
                'language': 'English',
                'level': 'B2',
                'length': '500',
                'topic': 'AI'
            },
            'status': 'completed'
        }
        mock_get_vocabs.return_value = []

        response = self.client.get(f"/articles/{self.article_id}/vocabularies")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 0)

    @patch('api.routes.articles.get_article')
    @patch('api.routes.articles.get_mongodb_client')
    def test_get_article_vocabularies_mongodb_unavailable(self, mock_client, mock_get_article):
        """Test 503 response when MongoDB is unavailable."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_client.return_value = None  # MongoDB unavailable

        response = self.client.get(f"/articles/{self.article_id}/vocabularies")

        self.assertEqual(response.status_code, 503)
        self.assertIn("Database service unavailable", response.json()['detail'])

    @patch('api.routes.articles.get_vocabularies')
    @patch('api.routes.articles.get_article')
    @patch('api.routes.articles.get_mongodb_client')
    def test_get_article_vocabularies_race_condition_article_deleted(self, mock_client, mock_get_article, mock_get_vocabs):
        """Test handling of race condition where article is deleted between validation and fetch."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_client.return_value = MagicMock()

        # First call (validation) returns article, second call returns None (deleted)
        mock_get_article.side_effect = [
            {
                '_id': self.article_id,
                'user_id': 'test-user-123',
                'inputs': {'language': 'English', 'level': 'B2', 'length': '500', 'topic': 'AI'},
                'status': 'completed'
            },
            None  # Article deleted between calls
        ]

        response = self.client.get(f"/articles/{self.article_id}/vocabularies")

        self.assertEqual(response.status_code, 404)
        self.assertIn("Article not found", response.json()['detail'])


if __name__ == '__main__':
    unittest.main()
