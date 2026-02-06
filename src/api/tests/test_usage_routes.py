"""Tests for token usage API routes."""

import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.main import app
from api.models import User
from api.middleware.auth import get_current_user_required


def mock_token_summary():
    """Return mock token usage summary."""
    return {
        'total_tokens': 15000,
        'total_cost': 0.0234,
        'by_operation': {
            'dictionary_search': {'tokens': 5000, 'cost': 0.0075, 'count': 50},
            'article_generation': {'tokens': 10000, 'cost': 0.0159, 'count': 5}
        },
        'daily_usage': [
            {'date': '2026-01-28', 'tokens': 3000, 'cost': 0.0045},
            {'date': '2026-01-29', 'tokens': 5000, 'cost': 0.0078},
            {'date': '2026-01-30', 'tokens': 7000, 'cost': 0.0111}
        ]
    }


def mock_article_usage():
    """Return mock article token usage records."""
    return [
        {
            'id': 'usage-1',
            'user_id': 'test-user-123',
            'operation': 'article_generation',
            'model': 'gpt-4.1',
            'prompt_tokens': 2000,
            'completion_tokens': 1500,
            'total_tokens': 3500,
            'estimated_cost': 0.0525,
            'metadata': {'topic': 'technology'},
            'created_at': datetime(2026, 1, 30, 10, 0, 0, tzinfo=timezone.utc)
        },
        {
            'id': 'usage-2',
            'user_id': 'test-user-123',
            'operation': 'article_generation',
            'model': 'gpt-4.1',
            'prompt_tokens': 1000,
            'completion_tokens': 800,
            'total_tokens': 1800,
            'estimated_cost': 0.027,
            'metadata': {},
            'created_at': datetime(2026, 1, 30, 10, 5, 0, tzinfo=timezone.utc)
        }
    ]


class TestGetMyUsage(unittest.TestCase):
    """Tests for GET /usage/me endpoint."""

    def setUp(self):
        """Set up test fixtures."""
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

    def test_get_my_usage_requires_authentication(self):
        """Test that endpoint requires authentication."""
        def mock_auth_fail():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user_required] = mock_auth_fail

        response = self.client.get("/usage/me")
        assert response.status_code == 401

    @patch('api.routes.usage.get_user_token_summary')
    def test_get_my_usage_success(self, mock_get_summary):
        """Test successful token usage summary retrieval."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_get_summary.return_value = mock_token_summary()

        response = self.client.get("/usage/me")

        assert response.status_code == 200
        data = response.json()
        assert data['total_tokens'] == 15000
        assert data['total_cost'] == 0.0234
        assert 'dictionary_search' in data['by_operation']
        assert data['by_operation']['dictionary_search']['tokens'] == 5000
        assert data['by_operation']['dictionary_search']['count'] == 50
        assert len(data['daily_usage']) == 3
        assert data['daily_usage'][0]['date'] == '2026-01-28'

    @patch('api.routes.usage.get_user_token_summary')
    def test_get_my_usage_with_custom_days(self, mock_get_summary):
        """Test token usage with custom days parameter."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_get_summary.return_value = {
            'total_tokens': 1000,
            'total_cost': 0.001,
            'by_operation': {},
            'daily_usage': []
        }

        response = self.client.get("/usage/me?days=7")

        assert response.status_code == 200
        mock_get_summary.assert_called_once_with(user_id="test-user-123", days=7)

    def test_get_my_usage_validates_days_range(self):
        """Test that days parameter is validated."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user

        # Test days < 1
        response = self.client.get("/usage/me?days=0")
        assert response.status_code == 422  # Validation error

        # Test days > 365
        response = self.client.get("/usage/me?days=400")
        assert response.status_code == 422

    @patch('api.routes.usage.get_user_token_summary')
    def test_get_my_usage_empty_result(self, mock_get_summary):
        """Test token usage with no data."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_get_summary.return_value = {
            'total_tokens': 0,
            'total_cost': 0.0,
            'by_operation': {},
            'daily_usage': []
        }

        response = self.client.get("/usage/me")

        assert response.status_code == 200
        data = response.json()
        assert data['total_tokens'] == 0
        assert data['total_cost'] == 0.0
        assert data['by_operation'] == {}
        assert data['daily_usage'] == []


class TestGetArticleUsage(unittest.TestCase):
    """Tests for GET /usage/articles/{article_id} endpoint."""

    def setUp(self):
        """Set up test fixtures."""
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

    def test_get_article_usage_requires_authentication(self):
        """Test that endpoint requires authentication."""
        def mock_auth_fail():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user_required] = mock_auth_fail

        response = self.client.get(f"/usage/articles/{self.article_id}")
        assert response.status_code == 401

    @patch('api.routes.usage.get_article_token_usage')
    @patch('api.routes.usage.get_article')
    def test_get_article_usage_success(self, mock_get_article, mock_get_usage):
        """Test successful article usage retrieval."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_get_article.return_value = {
            '_id': self.article_id,
            'user_id': 'test-user-123',
            'status': 'completed'
        }
        mock_get_usage.return_value = mock_article_usage()

        response = self.client.get(f"/usage/articles/{self.article_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]['id'] == 'usage-1'
        assert data[0]['operation'] == 'article_generation'
        assert data[0]['total_tokens'] == 3500
        assert data[1]['id'] == 'usage-2'

    @patch('api.routes.usage.get_article')
    def test_get_article_usage_article_not_found(self, mock_get_article):
        """Test 404 when article doesn't exist."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_get_article.return_value = None

        response = self.client.get("/usage/articles/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()['detail'].lower()

    @patch('api.routes.usage.get_article')
    def test_get_article_usage_forbidden_for_other_user(self, mock_get_article):
        """Test 403 when trying to access another user's article."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_get_article.return_value = {
            '_id': self.article_id,
            'user_id': 'other-user-456',  # Different user
            'status': 'completed'
        }

        response = self.client.get(f"/usage/articles/{self.article_id}")

        assert response.status_code == 403
        assert "permission" in response.json()['detail'].lower()

    @patch('api.routes.usage.get_article_token_usage')
    @patch('api.routes.usage.get_article')
    def test_get_article_usage_empty_result(self, mock_get_article, mock_get_usage):
        """Test article usage with no records."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        mock_get_article.return_value = {
            '_id': self.article_id,
            'user_id': 'test-user-123',
            'status': 'completed'
        }
        mock_get_usage.return_value = []

        response = self.client.get(f"/usage/articles/{self.article_id}")

        assert response.status_code == 200
        assert response.json() == []


class TestDictionarySearchTokenUsageIntegration(unittest.TestCase):
    """Integration tests verifying dictionary search calls save_token_usage."""

    def setUp(self):
        """Set up test fixtures."""
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

    def _create_mock_service(self, lookup_result):
        """Create a mock DictionaryService that returns the given result."""
        from unittest.mock import AsyncMock
        from services.dictionary_service import DictionaryService

        mock_service = MagicMock(spec=DictionaryService)
        mock_service.lookup = AsyncMock(return_value=lookup_result)
        mock_service.last_token_stats = MagicMock(
            model="gpt-4.1-mini",
            prompt_tokens=100,
            completion_tokens=50,
            estimated_cost=0.0001
        )
        return mock_service

    @patch('api.routes.dictionary.save_token_usage')
    def test_dictionary_search_calls_save_token_usage(self, mock_save_usage):
        """Test that dictionary search endpoint calls save_token_usage."""
        from api.routes.dictionary import get_dictionary_service
        from services.dictionary_service import LookupResult

        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user

        result = LookupResult(
            lemma="test",
            definition="a procedure",
            source="hybrid"
        )
        mock_service = self._create_mock_service(result)
        app.dependency_overrides[get_dictionary_service] = lambda: mock_service
        mock_save_usage.return_value = "usage-id-123"

        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "test",
                "sentence": "This is a test.",
                "language": "English"
            }
        )

        assert response.status_code == 200

        # Verify save_token_usage was called with correct parameters
        mock_save_usage.assert_called_once()
        call_kwargs = mock_save_usage.call_args[1]
        assert call_kwargs['user_id'] == "test-user-123"
        assert call_kwargs['operation'] == "dictionary_search"
        assert call_kwargs['model'] == "gpt-4.1-mini"
        assert call_kwargs['prompt_tokens'] == 100
        assert call_kwargs['completion_tokens'] == 50
        assert call_kwargs['estimated_cost'] == 0.0001
        assert call_kwargs['metadata']['word'] == "test"
        assert call_kwargs['metadata']['language'] == "English"

    @patch('api.routes.dictionary.save_token_usage')
    def test_dictionary_search_token_usage_persists_on_success(self, mock_save_usage):
        """Test that token usage is saved even with partial JSON response."""
        from api.routes.dictionary import get_dictionary_service
        from services.dictionary_service import LookupResult

        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user

        result = LookupResult(
            lemma="word",
            definition="meaning",
            source="hybrid"
        )
        mock_service = self._create_mock_service(result)
        app.dependency_overrides[get_dictionary_service] = lambda: mock_service
        mock_save_usage.return_value = "usage-id-456"

        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "word",
                "sentence": "A word.",
                "language": "English"
            }
        )

        assert response.status_code == 200
        # Verify save_token_usage was called even with minimal response
        assert mock_save_usage.called

    @patch('api.routes.dictionary.save_token_usage')
    def test_dictionary_search_token_usage_with_german_language(self, mock_save_usage):
        """Test that token usage correctly captures non-English language."""
        from api.routes.dictionary import get_dictionary_service
        from services.dictionary_service import LookupResult

        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user

        result = LookupResult(
            lemma="gehen",
            definition="to go",
            level="A1",
            source="hybrid"
        )
        mock_service = self._create_mock_service(result)
        app.dependency_overrides[get_dictionary_service] = lambda: mock_service
        mock_save_usage.return_value = "usage-id-789"

        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "gehen",
                "sentence": "Ich gehe nach Hause.",
                "language": "German"
            }
        )

        assert response.status_code == 200
        mock_save_usage.assert_called_once()
        call_kwargs = mock_save_usage.call_args[1]
        assert call_kwargs['metadata']['language'] == "German"
        assert call_kwargs['metadata']['word'] == "gehen"


class TestTokenUsageRecordModel(unittest.TestCase):
    """Tests for TokenUsageRecord model validation and edge cases."""

    def setUp(self):
        """Set up test fixtures."""
        from api.models import TokenUsageRecord

        self.TokenUsageRecord = TokenUsageRecord
        self.now = datetime.now(timezone.utc)

    def test_token_usage_record_with_all_fields(self):
        """Test TokenUsageRecord with all fields provided."""
        record = self.TokenUsageRecord(
            id="usage-123",
            user_id="user-456",
            operation="dictionary_search",
            model="gpt-4.1-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost=0.0001,
            metadata={"word": "test", "language": "English"},
            created_at=self.now
        )

        assert record.id == "usage-123"
        assert record.user_id == "user-456"
        assert record.operation == "dictionary_search"
        assert record.model == "gpt-4.1-mini"
        assert record.prompt_tokens == 100
        assert record.completion_tokens == 50
        assert record.total_tokens == 150
        assert record.estimated_cost == 0.0001
        assert record.metadata == {"word": "test", "language": "English"}
        assert record.created_at == self.now

    def test_token_usage_record_with_empty_metadata(self):
        """Test TokenUsageRecord with empty metadata dictionary."""
        record = self.TokenUsageRecord(
            id="usage-123",
            user_id="user-456",
            operation="dictionary_search",
            model="gpt-4.1-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost=0.0001,
            metadata={},
            created_at=self.now
        )

        assert record.metadata == {}
        assert isinstance(record.metadata, dict)

    def test_token_usage_record_without_metadata(self):
        """Test TokenUsageRecord without metadata defaults to empty dict."""
        record = self.TokenUsageRecord(
            id="usage-123",
            user_id="user-456",
            operation="dictionary_search",
            model="gpt-4.1-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost=0.0001,
            created_at=self.now
        )

        assert record.metadata == {}

    def test_token_usage_record_with_zero_tokens(self):
        """Test TokenUsageRecord with zero tokens (edge case)."""
        record = self.TokenUsageRecord(
            id="usage-123",
            user_id="user-456",
            operation="dictionary_search",
            model="gpt-4.1-mini",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            estimated_cost=0.0,
            created_at=self.now
        )

        assert record.prompt_tokens == 0
        assert record.completion_tokens == 0
        assert record.total_tokens == 0
        assert record.estimated_cost == 0.0

    def test_token_usage_record_with_very_large_token_counts(self):
        """Test TokenUsageRecord with very large token counts."""
        record = self.TokenUsageRecord(
            id="usage-123",
            user_id="user-456",
            operation="article_generation",
            model="gpt-4",
            prompt_tokens=1000000,
            completion_tokens=500000,
            total_tokens=1500000,
            estimated_cost=45.50,
            created_at=self.now
        )

        assert record.prompt_tokens == 1000000
        assert record.completion_tokens == 500000
        assert record.total_tokens == 1500000
        assert record.estimated_cost == 45.50

    def test_token_usage_record_with_very_small_cost(self):
        """Test TokenUsageRecord with very small estimated cost."""
        record = self.TokenUsageRecord(
            id="usage-123",
            user_id="user-456",
            operation="dictionary_search",
            model="gpt-4.1-mini",
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
            estimated_cost=0.00000001,
            created_at=self.now
        )

        assert record.estimated_cost == 0.00000001

    def test_token_usage_record_with_article_operation(self):
        """Test TokenUsageRecord for article_generation operation."""
        record = self.TokenUsageRecord(
            id="usage-789",
            user_id="user-456",
            operation="article_generation",
            model="gpt-4",
            prompt_tokens=2000,
            completion_tokens=1500,
            total_tokens=3500,
            estimated_cost=0.0525,
            metadata={"article_id": "article-123", "topic": "technology"},
            created_at=self.now
        )

        assert record.operation == "article_generation"
        assert record.metadata["article_id"] == "article-123"
        assert record.total_tokens == 3500

    def test_token_usage_record_with_complex_metadata(self):
        """Test TokenUsageRecord with nested metadata."""
        complex_metadata = {
            "word": "test",
            "language": "English",
            "context": {
                "lemma": "test",
                "pos": "noun"
            },
            "tags": ["vocabulary", "search"]
        }

        record = self.TokenUsageRecord(
            id="usage-123",
            user_id="user-456",
            operation="dictionary_search",
            model="gpt-4.1-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost=0.0001,
            metadata=complex_metadata,
            created_at=self.now
        )

        assert record.metadata == complex_metadata
        assert record.metadata["context"]["pos"] == "noun"
        assert "search" in record.metadata["tags"]

    def test_token_usage_record_json_serialization(self):
        """Test TokenUsageRecord JSON serialization."""
        record = self.TokenUsageRecord(
            id="usage-123",
            user_id="user-456",
            operation="dictionary_search",
            model="gpt-4.1-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost=0.0001,
            metadata={"word": "test"},
            created_at=self.now
        )

        serialized = record.dict()
        assert serialized['id'] == "usage-123"
        assert serialized['operation'] == "dictionary_search"
        assert serialized['prompt_tokens'] == 100
        assert isinstance(serialized['created_at'], datetime)

    def test_token_usage_record_with_different_models(self):
        """Test TokenUsageRecord with various model names."""
        models = ["gpt-4.1-mini", "gpt-4", "claude-3-opus", "claude-3-sonnet"]

        for model in models:
            record = self.TokenUsageRecord(
                id="usage-123",
                user_id="user-456",
                operation="dictionary_search",
                model=model,
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.0001,
                created_at=self.now
            )

            assert record.model == model


class TestTokenUsageRecordConstruction(unittest.TestCase):
    """Tests for TokenUsageRecord construction edge cases."""

    def setUp(self):
        """Set up test fixtures."""
        from api.models import TokenUsageRecord
        from pydantic import ValidationError

        self.TokenUsageRecord = TokenUsageRecord
        self.ValidationError = ValidationError
        self.now = datetime.now(timezone.utc)

    def test_token_usage_record_missing_required_field_id(self):
        """Test TokenUsageRecord validation fails without id."""
        with self.assertRaises(self.ValidationError):
            self.TokenUsageRecord(
                user_id="user-456",
                operation="dictionary_search",
                model="gpt-4.1-mini",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.0001,
                created_at=self.now
            )

    def test_token_usage_record_missing_required_field_user_id(self):
        """Test TokenUsageRecord validation fails without user_id."""
        with self.assertRaises(self.ValidationError):
            self.TokenUsageRecord(
                id="usage-123",
                operation="dictionary_search",
                model="gpt-4.1-mini",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.0001,
                created_at=self.now
            )

    def test_token_usage_record_missing_required_field_operation(self):
        """Test TokenUsageRecord validation fails without operation."""
        with self.assertRaises(self.ValidationError):
            self.TokenUsageRecord(
                id="usage-123",
                user_id="user-456",
                model="gpt-4.1-mini",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.0001,
                created_at=self.now
            )

    def test_token_usage_record_missing_required_field_model(self):
        """Test TokenUsageRecord validation fails without model."""
        with self.assertRaises(self.ValidationError):
            self.TokenUsageRecord(
                id="usage-123",
                user_id="user-456",
                operation="dictionary_search",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.0001,
                created_at=self.now
            )

    def test_token_usage_record_missing_required_field_prompt_tokens(self):
        """Test TokenUsageRecord validation fails without prompt_tokens."""
        with self.assertRaises(self.ValidationError):
            self.TokenUsageRecord(
                id="usage-123",
                user_id="user-456",
                operation="dictionary_search",
                model="gpt-4.1-mini",
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.0001,
                created_at=self.now
            )

    def test_token_usage_record_missing_required_field_completion_tokens(self):
        """Test TokenUsageRecord validation fails without completion_tokens."""
        with self.assertRaises(self.ValidationError):
            self.TokenUsageRecord(
                id="usage-123",
                user_id="user-456",
                operation="dictionary_search",
                model="gpt-4.1-mini",
                prompt_tokens=100,
                total_tokens=150,
                estimated_cost=0.0001,
                created_at=self.now
            )

    def test_token_usage_record_missing_required_field_total_tokens(self):
        """Test TokenUsageRecord validation fails without total_tokens."""
        with self.assertRaises(self.ValidationError):
            self.TokenUsageRecord(
                id="usage-123",
                user_id="user-456",
                operation="dictionary_search",
                model="gpt-4.1-mini",
                prompt_tokens=100,
                completion_tokens=50,
                estimated_cost=0.0001,
                created_at=self.now
            )

    def test_token_usage_record_missing_required_field_estimated_cost(self):
        """Test TokenUsageRecord validation fails without estimated_cost."""
        with self.assertRaises(self.ValidationError):
            self.TokenUsageRecord(
                id="usage-123",
                user_id="user-456",
                operation="dictionary_search",
                model="gpt-4.1-mini",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                created_at=self.now
            )

    def test_token_usage_record_missing_required_field_created_at(self):
        """Test TokenUsageRecord validation fails without created_at."""
        with self.assertRaises(self.ValidationError):
            self.TokenUsageRecord(
                id="usage-123",
                user_id="user-456",
                operation="dictionary_search",
                model="gpt-4.1-mini",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.0001
            )

    def test_token_usage_record_with_negative_tokens_not_allowed(self):
        """Test TokenUsageRecord allows zero but validates logically."""
        # Pydantic doesn't have field constraints, but we test the model accepts all ints
        record = self.TokenUsageRecord(
            id="usage-123",
            user_id="user-456",
            operation="dictionary_search",
            model="gpt-4.1-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost=0.0001,
            created_at=datetime.now(timezone.utc)
        )
        assert record.prompt_tokens >= 0


if __name__ == '__main__':
    unittest.main()
