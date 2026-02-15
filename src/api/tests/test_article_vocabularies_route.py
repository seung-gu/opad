"""Unit tests for article vocabularies route."""

import unittest
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from api.main import app
from api.models import UserResponse
from api.security import get_current_user_required
from api.dependencies import get_article_repo, get_vocab_repo
from adapter.fake.article_repository import FakeArticleRepository
from adapter.fake.vocabulary_repository import FakeVocabularyRepository
from domain.model.article import ArticleInputs, ArticleStatus
from domain.model.vocabulary import GrammaticalInfo


class TestGetArticleVocabularies(unittest.TestCase):
    """Test cases for GET /articles/{article_id}/vocabularies endpoint."""

    def setUp(self):
        """Set up test client and fixtures."""
        self.client = TestClient(app)
        self.mock_user = UserResponse(
            id="test-user-123",
            email="test@example.com",
            name="Test User",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            provider="email"
        )
        self.article_id = "test-article-123"
        self.repo = FakeArticleRepository()
        self.vocab_repo = FakeVocabularyRepository()

    def tearDown(self):
        """Clean up dependency overrides."""
        app.dependency_overrides.clear()

    def _setup_auth_and_repo(self):
        """Common setup for authenticated requests with fake repo."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        app.dependency_overrides[get_article_repo] = lambda: self.repo
        app.dependency_overrides[get_vocab_repo] = lambda: self.vocab_repo

    def _create_test_article(self, user_id="test-user-123", status=ArticleStatus.COMPLETED):
        """Create a test article in the fake repo."""
        self.repo.save_metadata(
            article_id=self.article_id,
            inputs=ArticleInputs(language='English', level='B2', length='500', topic='AI'),
            user_id=user_id,
        )
        if status == ArticleStatus.COMPLETED:
            self.repo.save_content(self.article_id, "Test content")

    def test_get_article_vocabularies_success(self):
        """Test successful retrieval of article vocabularies."""
        self._setup_auth_and_repo()
        self._create_test_article()
        self.vocab_repo.save(
            article_id=self.article_id,
            word='testing',
            lemma='test',
            definition='a procedure',
            sentence='This is a test.',
            language='English',
            user_id='test-user-123',
        )

        response = self.client.get(f"/articles/{self.article_id}/vocabularies")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['lemma'], 'test')
        self.assertEqual(data[0]['article_id'], self.article_id)

    def test_get_article_vocabularies_article_not_found(self):
        """Test 404 response when article doesn't exist."""
        self._setup_auth_and_repo()
        # Don't create article → repo.get_by_id returns None

        response = self.client.get(f"/articles/{self.article_id}/vocabularies")

        self.assertEqual(response.status_code, 404)
        self.assertIn("Article not found", response.json()['detail'])

    def test_get_article_vocabularies_unauthorized_access(self):
        """Test 403 response when user doesn't own the article."""
        self._setup_auth_and_repo()
        self._create_test_article(user_id="different-user-456")

        response = self.client.get(f"/articles/{self.article_id}/vocabularies")

        self.assertEqual(response.status_code, 403)
        self.assertIn("don't have permission", response.json()['detail'])

    def test_get_article_vocabularies_requires_authentication(self):
        """Test that endpoint requires authentication."""
        from fastapi import HTTPException

        def mock_auth_fail():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user_required] = mock_auth_fail

        response = self.client.get(f"/articles/{self.article_id}/vocabularies")

        self.assertEqual(response.status_code, 401)

    def test_get_article_vocabularies_empty_result(self):
        """Test successful response with no vocabularies."""
        self._setup_auth_and_repo()
        self._create_test_article()

        response = self.client.get(f"/articles/{self.article_id}/vocabularies")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 0)


if __name__ == '__main__':
    unittest.main()
