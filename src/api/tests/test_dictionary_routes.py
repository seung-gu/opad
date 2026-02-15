"""Unit tests for dictionary routes."""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient
from api.main import app
from api.models import UserResponse
from api.security import get_current_user_required
from api.dependencies import get_token_usage_repo, get_vocab_repo
from adapter.fake.vocabulary_repository import FakeVocabularyRepository
from domain.model.vocabulary import GrammaticalInfo
from api.routes.dictionary import get_dictionary_service
from services.dictionary_service import DictionaryService, LookupResult, LookupRequest
from utils.llm import TokenUsageStats


def mock_token_stats() -> TokenUsageStats:
    """Create a mock TokenUsageStats for testing."""
    return TokenUsageStats(
        model="gpt-4.1-mini",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        estimated_cost=0.0001,
        provider="openai"
    )


class TestSearchWordRoute(unittest.TestCase):
    """Test cases for POST /dictionary/search endpoint."""

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
        self.mock_token_repo = MagicMock()
        self.mock_token_repo.save.return_value = "usage-id-stub"

    def tearDown(self):
        """Clean up dependency overrides."""
        app.dependency_overrides.clear()

    def _setup_overrides(self):
        """Set up common dependency overrides for authenticated requests."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        app.dependency_overrides[get_token_usage_repo] = lambda: self.mock_token_repo

    def _create_mock_service(self, lookup_result: LookupResult) -> DictionaryService:
        """Create a mock DictionaryService that returns the given result."""
        mock_service = MagicMock(spec=DictionaryService)
        mock_service.lookup = AsyncMock(return_value=lookup_result)
        mock_service.last_token_stats = MagicMock(
            model="gpt-4.1-mini",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost=0.0001
        )
        return mock_service

    def test_search_word_success_with_valid_json(self):
        """Test successful word search with valid JSON response from LLM."""
        self._setup_overrides()

        # Create mock service with expected result
        result = LookupResult(
            lemma="test",
            definition="a procedure",
            related_words=["test", "testing"],
            pos="noun",
            gender=None,
            conjugations=None,
            level="B1",
            source="hybrid"
        )
        mock_service = self._create_mock_service(result)
        app.dependency_overrides[get_dictionary_service] = lambda: mock_service

        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "testing",
                "sentence": "I am testing the system.",
                "language": "English"
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["lemma"], "test")
        self.assertEqual(data["definition"], "a procedure")
        self.assertEqual(data["related_words"], ["test", "testing"])
        self.assertEqual(data["pos"], "noun")
        self.assertIsNone(data["gender"])
        self.assertIsNone(data["conjugations"])
        self.assertEqual(data["level"], "B1")

    def test_search_word_success_without_related_words(self):
        """Test successful word search when LLM doesn't return related_words."""
        self._setup_overrides()

        result = LookupResult(
            lemma="run",
            definition="to move quickly",
            related_words=None,
            pos=None,
            gender=None,
            conjugations=None,
            level=None,
            source="llm"
        )
        mock_service = self._create_mock_service(result)
        app.dependency_overrides[get_dictionary_service] = lambda: mock_service

        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "running",
                "sentence": "I am running fast.",
                "language": "English"
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["lemma"], "run")
        self.assertEqual(data["definition"], "to move quickly")
        self.assertIsNone(data["related_words"])
        self.assertIsNone(data["pos"])
        self.assertIsNone(data["gender"])
        self.assertIsNone(data["conjugations"])
        self.assertIsNone(data["level"])

    def test_search_word_fallback_on_json_parse_failure(self):
        """Test fallback behavior when JSON parsing fails."""
        self._setup_overrides()

        # Service returns fallback result
        result = LookupResult(
            lemma="test",
            definition="This is a simple definition without JSON",
            source="llm"
        )
        mock_service = self._create_mock_service(result)
        app.dependency_overrides[get_dictionary_service] = lambda: mock_service

        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "test",
                "sentence": "This is a test.",
                "language": "English"
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["lemma"], "test")
        self.assertEqual(data["definition"], "This is a simple definition without JSON")

    def test_search_word_truncates_long_non_json_response(self):
        """Test that long non-JSON responses are truncated."""
        self._setup_overrides()

        # Service returns "Definition not found" for long content
        result = LookupResult(
            lemma="test",
            definition="Definition not found",
            source="llm"
        )
        mock_service = self._create_mock_service(result)
        app.dependency_overrides[get_dictionary_service] = lambda: mock_service

        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "test",
                "sentence": "This is a test.",
                "language": "English"
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["lemma"], "test")
        self.assertEqual(data["definition"], "Definition not found")

    def test_search_word_requires_authentication(self):
        """Test that search_word requires authentication."""
        from fastapi import HTTPException

        def mock_auth_fail():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user_required] = mock_auth_fail

        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "test",
                "sentence": "This is a test.",
                "language": "English"
            }
        )

        self.assertEqual(response.status_code, 401)

    def test_search_word_invalid_input_validation(self):
        """Test input validation for search_word."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user

        # Test empty word
        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "",
                "sentence": "This is a test.",
                "language": "English"
            }
        )
        self.assertEqual(response.status_code, 422)

        # Test empty sentence
        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "test",
                "sentence": "",
                "language": "English"
            }
        )
        self.assertEqual(response.status_code, 422)

        # Test word too long
        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "x" * 101,
                "sentence": "This is a test.",
                "language": "English"
            }
        )
        self.assertEqual(response.status_code, 422)

    def test_search_word_handles_llm_timeout_error(self):
        """Test handling of LLM timeout errors."""
        import litellm

        self._setup_overrides()

        # Create mock service that raises timeout
        mock_service = MagicMock(spec=DictionaryService)
        mock_service.lookup = AsyncMock(
            side_effect=litellm.Timeout("Request timeout", llm_provider="openai", model="gpt-4o-mini")
        )
        app.dependency_overrides[get_dictionary_service] = lambda: mock_service

        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "test",
                "sentence": "This is a test.",
                "language": "English"
            }
        )

        self.assertEqual(response.status_code, 504)

    def test_search_word_handles_llm_api_error(self):
        """Test handling of LLM API errors."""
        import litellm

        self._setup_overrides()

        # Create mock service that raises API error
        mock_service = MagicMock(spec=DictionaryService)
        mock_service.lookup = AsyncMock(
            side_effect=litellm.APIError(
                status_code=500,
                message="Internal server error",
                llm_provider="openai",
                model="gpt-4o-mini"
            )
        )
        app.dependency_overrides[get_dictionary_service] = lambda: mock_service

        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "test",
                "sentence": "This is a test.",
                "language": "English"
            }
        )

        self.assertEqual(response.status_code, 502)

    def test_search_word_with_verb_conjugations(self):
        """Test word search for verb with conjugations."""
        self._setup_overrides()

        result = LookupResult(
            lemma="gehen",
            definition="to go, to walk",
            related_words=["gehen"],
            pos="verb",
            gender=None,
            conjugations={
                "present": "gehe, gehst, geht",
                "past": "ging",
                "participle": "gegangen"
            },
            level="A1",
            source="hybrid"
        )
        mock_service = self._create_mock_service(result)
        app.dependency_overrides[get_dictionary_service] = lambda: mock_service

        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "gehen",
                "sentence": "Ich gehe nach Hause.",
                "language": "German"
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["lemma"], "gehen")
        self.assertEqual(data["pos"], "verb")
        self.assertIsNotNone(data["conjugations"])
        self.assertEqual(data["conjugations"]["past"], "ging")
        self.assertEqual(data["conjugations"]["participle"], "gegangen")
        self.assertEqual(data["level"], "A1")

    def test_search_word_with_german_noun_gender(self):
        """Test word search for German noun with gender."""
        self._setup_overrides()

        result = LookupResult(
            lemma="Hund",
            definition="dog",
            related_words=["Hund"],
            pos="noun",
            gender="der",
            conjugations=None,
            level="A1",
            source="hybrid"
        )
        mock_service = self._create_mock_service(result)
        app.dependency_overrides[get_dictionary_service] = lambda: mock_service

        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "Hund",
                "sentence": "Der Hund ist groß.",
                "language": "German"
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["lemma"], "Hund")
        self.assertEqual(data["pos"], "noun")
        self.assertEqual(data["gender"], "der")
        self.assertIsNone(data["conjugations"])
        self.assertEqual(data["level"], "A1")


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

    def test_get_vocabularies_list_success(self):
        """Test successful retrieval of vocabulary list."""
        self._setup()
        # Save same lemma twice to get count=2
        for article_id in ['article-1', 'article-2']:
            self.vocab_repo.save(
                article_id=article_id, word='testing', lemma='test',
                definition='a procedure', sentence='This is a test.',
                language='English', user_id='test-user-123',
                grammar=GrammaticalInfo(pos='noun', level='B1'),
            )

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
        self.vocab_repo.save(
            article_id='a1', word='Hund', lemma='Hund',
            definition='dog', sentence='Der Hund.',
            language='German', user_id='test-user-123',
        )
        self.vocab_repo.save(
            article_id='a2', word='dog', lemma='dog',
            definition='dog', sentence='The dog.',
            language='English', user_id='test-user-123',
        )

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


if __name__ == '__main__':
    unittest.main()
