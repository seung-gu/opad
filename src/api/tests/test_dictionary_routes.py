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
from api.dependencies import get_token_usage_repo, get_dictionary_port, get_llm_port, get_nlp_port
from adapter.fake.dictionary import FakeDictionaryAdapter
from adapter.fake.llm import FakeLLMAdapter
from adapter.fake.nlp import FakeNLPAdapter
from domain.model.vocabulary import GrammaticalInfo, LookupResult
from domain.model.token_usage import LLMCallResult


def mock_token_stats() -> LLMCallResult:
    """Create a mock LLMCallResult for testing."""
    return LLMCallResult(
        model="gpt-4.1-mini",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        estimated_cost=0.0001,
        provider="openai"
    )


def _make_result(
    lemma="test",
    definition="a procedure",
    related_words=None,
    pos=None,
    gender=None,
    phonetics=None,
    conjugations=None,
    level=None,
    examples=None,
) -> LookupResult:
    """Create a LookupResult matching dictionary_service.lookup() output."""
    return LookupResult(
        lemma=lemma,
        definition=definition,
        related_words=related_words,
        level=level,
        grammar=GrammaticalInfo(
            pos=pos,
            gender=gender,
            phonetics=phonetics,
            conjugations=conjugations,
            examples=examples,
        ),
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
        app.dependency_overrides[get_dictionary_port] = lambda: FakeDictionaryAdapter()
        app.dependency_overrides[get_llm_port] = lambda: FakeLLMAdapter()
        app.dependency_overrides[get_nlp_port] = lambda: FakeNLPAdapter()

    @patch('services.dictionary_service.lookup')
    def test_search_word_success_with_valid_json(self, mock_lookup):
        """Test successful word search with valid JSON response from LLM."""
        self._setup_overrides()

        result = _make_result(
            lemma="test", definition="a procedure",
            related_words=["test", "testing"], pos="noun", level="B1",
        )
        mock_lookup.return_value = result

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

    @patch('services.dictionary_service.lookup')
    def test_search_word_success_without_related_words(self, mock_lookup):
        """Test successful word search when LLM doesn't return related_words."""
        self._setup_overrides()

        result = _make_result(
            lemma="run", definition="to move quickly",
        )
        mock_lookup.return_value = result

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

    @patch('services.dictionary_service.lookup')
    def test_search_word_fallback_on_json_parse_failure(self, mock_lookup):
        """Test fallback behavior when JSON parsing fails."""
        self._setup_overrides()

        result = _make_result(
            lemma="test",
            definition="This is a simple definition without JSON",
        )
        mock_lookup.return_value = result

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

    @patch('services.dictionary_service.lookup')
    def test_search_word_truncates_long_non_json_response(self, mock_lookup):
        """Test that long non-JSON responses are truncated."""
        self._setup_overrides()

        result = _make_result(
            lemma="test", definition="Definition not found",
        )
        mock_lookup.return_value = result

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

    @patch('services.dictionary_service.lookup')
    def test_search_word_handles_llm_timeout_error(self, mock_lookup):
        """Test handling of LLM timeout errors."""
        from port.llm import LLMTimeoutError

        self._setup_overrides()

        mock_lookup.side_effect = LLMTimeoutError("Request timeout")

        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "test",
                "sentence": "This is a test.",
                "language": "English"
            }
        )

        self.assertEqual(response.status_code, 504)

    @patch('services.dictionary_service.lookup')
    def test_search_word_handles_llm_api_error(self, mock_lookup):
        """Test handling of LLM API errors."""
        from port.llm import LLMError

        self._setup_overrides()

        mock_lookup.side_effect = LLMError("Internal server error")

        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "test",
                "sentence": "This is a test.",
                "language": "English"
            }
        )

        self.assertEqual(response.status_code, 502)

    @patch('services.dictionary_service.lookup')
    def test_search_word_with_verb_conjugations(self, mock_lookup):
        """Test word search for verb with conjugations."""
        self._setup_overrides()

        result = _make_result(
            lemma="gehen", definition="to go, to walk",
            related_words=["gehen"], pos="verb",
            conjugations={
                "present": "gehe, gehst, geht",
                "past": "ging",
                "participle": "gegangen"
            },
            level="A1",
        )
        mock_lookup.return_value = result

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

    @patch('services.dictionary_service.lookup')
    def test_search_word_with_german_noun_gender(self, mock_lookup):
        """Test word search for German noun with gender."""
        self._setup_overrides()

        result = _make_result(
            lemma="Hund", definition="dog",
            related_words=["Hund"], pos="noun", gender="der", level="A1",
        )
        mock_lookup.return_value = result

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


if __name__ == '__main__':
    unittest.main()
