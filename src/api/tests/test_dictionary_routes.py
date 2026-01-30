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
from api.models import User
from api.middleware.auth import get_current_user_required
from utils.llm import TokenUsageStats


def mock_stats() -> TokenUsageStats:
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
        self.mock_user = User(
            id="test-user-123",
            email="test@example.com",
            name="Test User",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            provider="email"
        )

    def tearDown(self):
        """Clean up dependency overrides."""
        app.dependency_overrides.clear()

    @patch('api.routes.dictionary.call_llm_with_tracking')
    @patch('api.routes.dictionary.build_word_definition_prompt')
    def test_search_word_success_with_valid_json(self, mock_prompt, mock_llm):
        """Test successful word search with valid JSON response from LLM."""
        # Override authentication dependency
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user

        # Mock prompt builder
        mock_prompt.return_value = "test prompt"

        # Mock LLM response with valid JSON including new fields
        mock_llm.return_value = ('''{
            "lemma": "test",
            "definition": "a procedure",
            "related_words": ["test", "testing"],
            "pos": "noun",
            "gender": null,
            "conjugations": null,
            "level": "B1"
        }''', mock_stats())

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

    @patch('api.routes.dictionary.call_llm_with_tracking')
    @patch('api.routes.dictionary.build_word_definition_prompt')
    def test_search_word_success_without_related_words(self, mock_prompt, mock_llm):
        """Test successful word search when LLM doesn't return related_words."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_prompt.return_value = "test prompt"
        mock_llm.return_value = ('{"lemma": "run", "definition": "to move quickly"}', mock_stats())

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
        # New fields should be None if not provided by LLM
        self.assertIsNone(data["pos"])
        self.assertIsNone(data["gender"])
        self.assertIsNone(data["conjugations"])
        self.assertIsNone(data["level"])

    @patch('api.routes.dictionary.call_llm_with_tracking')
    @patch('api.routes.dictionary.build_word_definition_prompt')
    def test_search_word_fallback_on_json_parse_failure(self, mock_prompt, mock_llm):
        """Test fallback behavior when JSON parsing fails."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_prompt.return_value = "test prompt"
        # Return non-JSON content (short enough to be used as definition)
        mock_llm.return_value = ("This is a simple definition without JSON", mock_stats())

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
        # Should use original word as lemma
        self.assertEqual(data["lemma"], "test")
        # Should use content as definition
        self.assertEqual(data["definition"], "This is a simple definition without JSON")

    @patch('api.routes.dictionary.call_llm_with_tracking')
    @patch('api.routes.dictionary.build_word_definition_prompt')
    def test_search_word_truncates_long_non_json_response(self, mock_prompt, mock_llm):
        """Test that long non-JSON responses are truncated."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_prompt.return_value = "test prompt"
        # Return very long non-JSON content
        mock_llm.return_value = ("x" * 1000, mock_stats())

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
        # Should return "Definition not found" for long content
        self.assertEqual(data["definition"], "Definition not found")

    def test_search_word_requires_authentication(self):
        """Test that search_word requires authentication."""
        from fastapi import HTTPException

        # Override dependency to raise authentication error
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

    @patch('api.routes.dictionary.call_llm_with_tracking')
    def test_search_word_invalid_input_validation(self, mock_llm):
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

    @patch('api.routes.dictionary.call_llm_with_tracking')
    @patch('api.routes.dictionary.build_word_definition_prompt')
    def test_search_word_handles_llm_timeout_error(self, mock_prompt, mock_llm):
        """Test handling of LLM timeout errors."""
        import litellm

        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_prompt.return_value = "test prompt"
        # Simulate timeout using LiteLLM's Timeout exception
        mock_llm.side_effect = litellm.Timeout("Request timeout", llm_provider="openai", model="gpt-4o-mini")

        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "test",
                "sentence": "This is a test.",
                "language": "English"
            }
        )

        # Should return 504 Gateway Timeout
        self.assertEqual(response.status_code, 504)

    @patch('api.routes.dictionary.call_llm_with_tracking')
    @patch('api.routes.dictionary.build_word_definition_prompt')
    def test_search_word_handles_llm_api_error(self, mock_prompt, mock_llm):
        """Test handling of LLM API errors."""
        import litellm

        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_prompt.return_value = "test prompt"
        # Simulate API error using LiteLLM's APIError
        mock_llm.side_effect = litellm.APIError(
            status_code=500,
            message="Internal server error",
            llm_provider="openai",
            model="gpt-4o-mini"
        )

        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "test",
                "sentence": "This is a test.",
                "language": "English"
            }
        )

        # Should return 502 for APIError from LiteLLM
        self.assertEqual(response.status_code, 502)

    @patch('api.routes.dictionary.call_llm_with_tracking')
    @patch('api.routes.dictionary.build_word_definition_prompt')
    def test_search_word_with_verb_conjugations(self, mock_prompt, mock_llm):
        """Test word search for verb with conjugations."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_prompt.return_value = "test prompt"

        # Mock LLM response with verb conjugations
        mock_llm.return_value = ('''{
            "lemma": "gehen",
            "definition": "to go, to walk",
            "related_words": ["gehen"],
            "pos": "verb",
            "gender": null,
            "conjugations": {
                "present": "gehe, gehst, geht",
                "past": "ging",
                "perfect": "gegangen"
            },
            "level": "A1"
        }''', mock_stats())

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
        self.assertEqual(data["conjugations"]["perfect"], "gegangen")
        self.assertEqual(data["level"], "A1")

    @patch('api.routes.dictionary.call_llm_with_tracking')
    @patch('api.routes.dictionary.build_word_definition_prompt')
    def test_search_word_with_german_noun_gender(self, mock_prompt, mock_llm):
        """Test word search for German noun with gender."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_prompt.return_value = "test prompt"

        # Mock LLM response with German noun gender
        mock_llm.return_value = ('''{
            "lemma": "Hund",
            "definition": "dog",
            "related_words": ["Hund"],
            "pos": "noun",
            "gender": "der",
            "conjugations": null,
            "level": "A1"
        }''', mock_stats())

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
        self.mock_user = User(
            id="test-user-123",
            email="test@example.com",
            name="Test User",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            provider="email"
        )

    def tearDown(self):
        """Clean up dependency overrides."""
        app.dependency_overrides.clear()

    @patch('api.routes.dictionary.get_vocabulary_counts')
    def test_get_vocabularies_list_success(self, mock_get_counts):
        """Test successful retrieval of vocabulary list."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_get_counts.return_value = [
            {
                'id': 'vocab-1',
                'article_id': 'article-1',
                'language': 'English',
                'lemma': 'test',
                'count': 5,
                'article_ids': ['article-1', 'article-2'],
                'definition': 'a procedure',
                'sentence': 'This is a test.',
                'word': 'testing',
                'created_at': datetime.now(timezone.utc),
                'related_words': None,
                'span_id': None,
                'user_id': 'test-user-123',
                'pos': 'noun',
                'gender': None,
                'conjugations': None,
                'level': 'B1'
            }
        ]

        response = self.client.get("/dictionary/vocabularies")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['lemma'], 'test')
        self.assertEqual(data[0]['count'], 5)
        self.assertEqual(data[0]['pos'], 'noun')
        self.assertEqual(data[0]['level'], 'B1')

    @patch('api.routes.dictionary.get_vocabulary_counts')
    def test_get_vocabularies_list_with_language_filter(self, mock_get_counts):
        """Test vocabulary list with language filter."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_get_counts.return_value = []

        response = self.client.get("/dictionary/vocabularies?language=German")

        self.assertEqual(response.status_code, 200)
        # Verify language filter was passed
        mock_get_counts.assert_called_once_with(
            language='German',
            user_id='test-user-123',
            skip=0,
            limit=100
        )

    @patch('api.routes.dictionary.get_vocabulary_counts')
    def test_get_vocabularies_list_with_pagination(self, mock_get_counts):
        """Test vocabulary list with pagination parameters."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_get_counts.return_value = []

        response = self.client.get("/dictionary/vocabularies?skip=10&limit=50")

        self.assertEqual(response.status_code, 200)
        # Verify pagination was passed
        mock_get_counts.assert_called_once_with(
            language=None,
            user_id='test-user-123',
            skip=10,
            limit=50
        )

    @patch('api.routes.dictionary.get_vocabulary_counts')
    def test_get_vocabularies_list_enforces_max_limit(self, mock_get_counts):
        """Test that vocabulary list enforces maximum limit of 1000."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_get_counts.return_value = []

        response = self.client.get("/dictionary/vocabularies?limit=5000")

        self.assertEqual(response.status_code, 200)
        # Verify limit was capped at 1000
        mock_get_counts.assert_called_once_with(
            language=None,
            user_id='test-user-123',
            skip=0,
            limit=1000
        )

    def test_get_vocabularies_list_requires_authentication(self):
        """Test that get_vocabularies_list requires authentication."""
        from fastapi import HTTPException

        # Override dependency to raise authentication error
        def mock_auth_fail():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user_required] = mock_auth_fail

        response = self.client.get("/dictionary/vocabularies")

        self.assertEqual(response.status_code, 401)

    @patch('api.routes.dictionary.get_vocabulary_counts')
    def test_get_vocabularies_list_empty_result(self, mock_get_counts):
        """Test vocabulary list with empty result."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_get_counts.return_value = []

        response = self.client.get("/dictionary/vocabularies")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 0)


if __name__ == '__main__':
    unittest.main()
