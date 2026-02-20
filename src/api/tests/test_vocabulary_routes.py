"""Unit tests for vocabulary routes."""

import unittest
import uuid
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from fastapi import HTTPException
from api.main import app
from api.models import UserResponse, VocabularyRequest
from api.security import get_current_user_required
from api.dependencies import get_vocab_repo, get_vocab_port
from adapter.fake.vocabulary_repository import FakeVocabularyRepository
from domain.model.vocabulary import GrammaticalInfo, Vocabulary
from domain.model.errors import NotFoundError, PermissionDeniedError


class TestGetVocabulariesList(unittest.TestCase):
    """Test cases for GET /dictionary/vocabularies endpoint."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)
        self.mock_user = UserResponse(
            id="test-user-123",
            email="test@example.com",
            name="Test User",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            provider="email"
        )
        self.vocab_repo = FakeVocabularyRepository()

    def tearDown(self):
        """Clean up dependency overrides."""
        app.dependency_overrides.clear()

    def _setup(self):
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        app.dependency_overrides[get_vocab_repo] = lambda: self.vocab_repo
        app.dependency_overrides[get_vocab_port] = lambda: self.vocab_repo

    def _make_vocab(self, **overrides) -> Vocabulary:
        """Create a Vocabulary domain object with sensible defaults."""
        defaults = dict(
            id=str(uuid.uuid4()),
            article_id='article-1',
            word='testing',
            lemma='test',
            definition='a procedure',
            sentence='This is a test.',
            language='English',
            created_at=datetime.now(timezone.utc),
            user_id='test-user-123',
        )
        defaults.update(overrides)
        return Vocabulary(**defaults)

    def test_get_vocabularies_list_success(self):
        """Test successful retrieval of vocabulary list."""
        self._setup()
        # Save same lemma twice to get count=2
        for article_id in ['article-1', 'article-2']:
            self.vocab_repo.save(self._make_vocab(
                article_id=article_id,
                level='B1',
                grammar=GrammaticalInfo(pos='noun'),
            ))

        response = self.client.get("/dictionary/vocabularies")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['lemma'], 'test')
        self.assertEqual(data[0]['count'], 2)
        self.assertEqual(data[0]['pos'], 'noun')
        self.assertEqual(data[0]['level'], 'B1')

    def test_get_vocabularies_list_with_language_filter(self):
        """Test vocabulary list with language filter."""
        self._setup()
        self.vocab_repo.save(self._make_vocab(
            article_id='a1', word='Hund', lemma='Hund',
            definition='dog', sentence='Der Hund.',
            language='German',
        ))
        self.vocab_repo.save(self._make_vocab(
            article_id='a2', word='dog', lemma='dog',
            definition='dog', sentence='The dog.',
            language='English',
        ))

        response = self.client.get("/dictionary/vocabularies?language=German")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['lemma'], 'Hund')

    def test_get_vocabularies_list_with_pagination(self):
        """Test vocabulary list with pagination parameters."""
        self._setup()

        response = self.client.get("/dictionary/vocabularies?skip=10&limit=50")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_vocabularies_list_enforces_max_limit(self):
        """Test that vocabulary list enforces maximum limit of 1000."""
        self._setup()

        response = self.client.get("/dictionary/vocabularies?limit=5000")

        self.assertEqual(response.status_code, 200)

    def test_get_vocabularies_list_requires_authentication(self):
        """Test that get_vocabularies_list requires authentication."""
        from fastapi import HTTPException

        def mock_auth_fail():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user_required] = mock_auth_fail

        response = self.client.get("/dictionary/vocabularies")

        self.assertEqual(response.status_code, 401)

    def test_get_vocabularies_list_empty_result(self):
        """Test vocabulary list with empty result."""
        self._setup()

        response = self.client.get("/dictionary/vocabularies")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 0)


class TestAddVocabulary(unittest.TestCase):
    """Test cases for POST /dictionary/vocabulary endpoint."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)
        self.mock_user = UserResponse(
            id="test-user-123",
            email="test@example.com",
            name="Test User",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            provider="email"
        )
        self.vocab_repo = FakeVocabularyRepository()

    def tearDown(self):
        """Clean up dependency overrides."""
        app.dependency_overrides.clear()

    def _setup(self):
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        app.dependency_overrides[get_vocab_repo] = lambda: self.vocab_repo
        app.dependency_overrides[get_vocab_port] = lambda: self.vocab_repo

    def test_add_vocabulary_success(self):
        """Test successful vocabulary addition returns 200 with VocabularyResponse fields."""
        self._setup()

        request_data = {
            "article_id": "article-123",
            "word": "testing",
            "lemma": "test",
            "definition": "a procedure",
            "sentence": "This is a test.",
            "language": "English",
            "related_words": None,
            "span_id": None,
            "pos": "noun",
            "gender": None,
            "phonetics": "/test/",
            "conjugations": None,
            "level": "B1",
            "examples": None
        }

        response = self.client.post("/dictionary/vocabulary", json=request_data)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['word'], 'testing')
        self.assertEqual(data['lemma'], 'test')
        self.assertEqual(data['definition'], 'a procedure')
        self.assertEqual(data['sentence'], 'This is a test.')
        self.assertEqual(data['language'], 'English')
        self.assertEqual(data['pos'], 'noun')
        self.assertEqual(data['level'], 'B1')
        self.assertEqual(data['user_id'], 'test-user-123')
        self.assertIn('id', data)
        self.assertIn('created_at', data)

    def test_add_vocabulary_requires_authentication(self):
        """Test that add_vocabulary requires authentication."""
        def mock_auth_fail():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user_required] = mock_auth_fail
        app.dependency_overrides[get_vocab_repo] = lambda: self.vocab_repo

        request_data = {
            "article_id": "article-123",
            "word": "testing",
            "lemma": "test",
            "definition": "a procedure",
            "sentence": "This is a test.",
            "language": "English"
        }

        response = self.client.post("/dictionary/vocabulary", json=request_data)

        self.assertEqual(response.status_code, 401)

    def test_add_vocabulary_save_failure_returns_500(self):
        """Test that save failure returns 500."""
        self._setup()

        # Create a mock repo that returns None from save
        class FailingRepository:
            def save(self, vocab):
                return None

            def get_by_id(self, vocab_id):
                return None

        app.dependency_overrides[get_vocab_repo] = lambda: FailingRepository()

        request_data = {
            "article_id": "article-123",
            "word": "testing",
            "lemma": "test",
            "definition": "a procedure",
            "sentence": "This is a test.",
            "language": "English"
        }

        response = self.client.post("/dictionary/vocabulary", json=request_data)

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertEqual(data['detail'], "Failed to save vocabulary")


class TestDeleteVocabulary(unittest.TestCase):
    """Test cases for DELETE /dictionary/vocabularies/{vocabulary_id} endpoint."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)
        self.mock_user = UserResponse(
            id="test-user-123",
            email="test@example.com",
            name="Test User",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            provider="email"
        )
        self.vocab_repo = FakeVocabularyRepository()

    def tearDown(self):
        """Clean up dependency overrides."""
        app.dependency_overrides.clear()

    def _setup(self):
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        app.dependency_overrides[get_vocab_repo] = lambda: self.vocab_repo
        app.dependency_overrides[get_vocab_port] = lambda: self.vocab_repo

    def _make_vocab(self, **overrides) -> Vocabulary:
        """Create a Vocabulary domain object with sensible defaults."""
        defaults = dict(
            id=str(uuid.uuid4()),
            article_id='article-1',
            word='testing',
            lemma='test',
            definition='a procedure',
            sentence='This is a test.',
            language='English',
            created_at=datetime.now(timezone.utc),
            user_id='test-user-123',
        )
        defaults.update(overrides)
        return Vocabulary(**defaults)

    def test_delete_vocabulary_success(self):
        """Test successful vocabulary deletion returns 200 with success message."""
        self._setup()

        # First, save a vocabulary to delete
        vocab = self._make_vocab()
        vocab_id = self.vocab_repo.save(vocab)

        response = self.client.delete(f"/dictionary/vocabularies/{vocab_id}")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['message'], "Vocabulary deleted successfully")

        # Verify it's actually deleted
        self.assertIsNone(self.vocab_repo.get_by_id(vocab_id))

    def test_delete_vocabulary_requires_authentication(self):
        """Test that delete_vocabulary_word requires authentication."""
        self._setup()

        # Save a vocabulary first
        vocab = self._make_vocab()
        vocab_id = self.vocab_repo.save(vocab)

        def mock_auth_fail():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user_required] = mock_auth_fail

        response = self.client.delete(f"/dictionary/vocabularies/{vocab_id}")

        self.assertEqual(response.status_code, 401)

    def test_delete_vocabulary_not_found(self):
        """Test that deleting non-existent vocabulary returns 404."""
        self._setup()

        non_existent_id = str(uuid.uuid4())

        response = self.client.delete(f"/dictionary/vocabularies/{non_existent_id}")

        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data['detail'], "Vocabulary not found")

    def test_delete_vocabulary_permission_denied(self):
        """Test that user cannot delete another user's vocabulary."""
        self._setup()

        # Save vocabulary owned by different user
        other_user_vocab = self._make_vocab(user_id="other-user-456")
        vocab_id = self.vocab_repo.save(other_user_vocab)

        response = self.client.delete(f"/dictionary/vocabularies/{vocab_id}")

        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data['detail'], "You don't have permission to delete this vocabulary")

        # Verify vocabulary still exists
        self.assertIsNotNone(self.vocab_repo.get_by_id(vocab_id))


if __name__ == '__main__':
    unittest.main()
