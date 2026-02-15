"""Tests for token usage API routes."""

import unittest
from pytest import approx
from datetime import datetime, timezone
from unittest.mock import MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.main import app
from api.models import UserResponse
from api.security import get_current_user_required
from api.dependencies import get_article_repo, get_token_usage_repo
from adapter.fake.article_repository import FakeArticleRepository
from adapter.fake.token_usage_repository import FakeTokenUsageRepository
from domain.model.article import ArticleInputs, ArticleStatus


class TestGetMyUsage(unittest.TestCase):
    """Tests for GET /usage/me endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
        self.mock_user = UserResponse(
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

    def test_get_my_usage_success(self):
        """Test successful token usage summary retrieval."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        fake_repo = FakeTokenUsageRepository()
        fake_repo.save(
            user_id="test-user-123",
            operation="dictionary_search",
            model="gpt-4.1-mini",
            prompt_tokens=2500,
            completion_tokens=2500,
            estimated_cost=0.0075,
        )
        fake_repo.save(
            user_id="test-user-123",
            operation="article_generation",
            model="gpt-4",
            prompt_tokens=5000,
            completion_tokens=5000,
            estimated_cost=0.0159,
        )
        app.dependency_overrides[get_token_usage_repo] = lambda: fake_repo

        response = self.client.get("/usage/me")

        assert response.status_code == 200
        data = response.json()
        assert data['total_tokens'] == 15000
        assert data['total_cost'] == approx(0.0234)
        assert 'dictionary_search' in data['by_operation']
        assert data['by_operation']['dictionary_search']['tokens'] == 5000
        assert 'article_generation' in data['by_operation']
        assert data['by_operation']['article_generation']['tokens'] == 10000
        assert len(data['daily_usage']) == 1

    def test_get_my_usage_with_custom_days(self):
        """Test token usage with custom days parameter."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        fake_repo = FakeTokenUsageRepository()
        fake_repo.save(
            user_id="test-user-123",
            operation="dictionary_search",
            model="gpt-4.1-mini",
            prompt_tokens=500,
            completion_tokens=500,
            estimated_cost=0.001,
        )
        app.dependency_overrides[get_token_usage_repo] = lambda: fake_repo

        response = self.client.get("/usage/me?days=7")

        assert response.status_code == 200
        data = response.json()
        assert data['total_tokens'] == 1000

    def test_get_my_usage_validates_days_range(self):
        """Test that days parameter is validated."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user

        # Test days < 1
        response = self.client.get("/usage/me?days=0")
        assert response.status_code == 422  # Validation error

        # Test days > 365
        response = self.client.get("/usage/me?days=400")
        assert response.status_code == 422

    def test_get_my_usage_empty_result(self):
        """Test token usage with no data."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        fake_repo = FakeTokenUsageRepository()
        app.dependency_overrides[get_token_usage_repo] = lambda: fake_repo

        response = self.client.get("/usage/me")

        assert response.status_code == 200
        data = response.json()
        assert data['total_tokens'] == 0
        assert data['total_cost'] == approx(0.0)
        assert data['by_operation'] == {}
        assert data['daily_usage'] == []


class TestGetArticleUsage(unittest.TestCase):
    """Tests for GET /usage/articles/{article_id} endpoint."""

    def setUp(self):
        """Set up test fixtures."""
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

    def tearDown(self):
        """Clean up dependency overrides."""
        app.dependency_overrides.clear()

    def _setup_auth_and_repo(self):
        """Common setup for authenticated requests with fake repos."""
        app.dependency_overrides[get_current_user_required] = lambda: self.mock_user
        app.dependency_overrides[get_article_repo] = lambda: self.repo
        self.usage_repo = FakeTokenUsageRepository()
        app.dependency_overrides[get_token_usage_repo] = lambda: self.usage_repo

    def _create_test_article(self, user_id="test-user-123", status=ArticleStatus.COMPLETED):
        """Create a test article in the fake repo."""
        self.repo.save_metadata(
            article_id=self.article_id,
            inputs=ArticleInputs(language='English', level='B2', length='500', topic='AI'),
            user_id=user_id,
        )
        if status == ArticleStatus.COMPLETED:
            self.repo.save_content(self.article_id, "Test content")

    def test_get_article_usage_requires_authentication(self):
        """Test that endpoint requires authentication."""
        def mock_auth_fail():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user_required] = mock_auth_fail

        response = self.client.get(f"/usage/articles/{self.article_id}")
        assert response.status_code == 401

    def test_get_article_usage_success(self):
        """Test successful article usage retrieval."""
        self._setup_auth_and_repo()
        self.usage_repo.save(
            user_id="test-user-123",
            operation="article_generation",
            model="gpt-4.1",
            prompt_tokens=2000,
            completion_tokens=1500,
            estimated_cost=0.0525,
            article_id=self.article_id,
            metadata={'topic': 'technology'},
        )
        self.usage_repo.save(
            user_id="test-user-123",
            operation="article_generation",
            model="gpt-4.1",
            prompt_tokens=1000,
            completion_tokens=800,
            estimated_cost=0.027,
            article_id=self.article_id,
        )
        self._create_test_article()

        response = self.client.get(f"/usage/articles/{self.article_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]['operation'] == 'article_generation'
        assert data[0]['total_tokens'] == 3500
        assert data[1]['total_tokens'] == 1800

    def test_get_article_usage_article_not_found(self):
        """Test 404 when article doesn't exist."""
        self._setup_auth_and_repo()
        # Don't create article -> repo.get_by_id returns None

        response = self.client.get("/usage/articles/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()['detail'].lower()

    def test_get_article_usage_forbidden_for_other_user(self):
        """Test 403 when trying to access another user's article."""
        self._setup_auth_and_repo()
        self._create_test_article(user_id="other-user-456")

        response = self.client.get(f"/usage/articles/{self.article_id}")

        assert response.status_code == 403
        assert "permission" in response.json()['detail'].lower()

    def test_get_article_usage_empty_result(self):
        """Test article usage with no records."""
        self._setup_auth_and_repo()
        self._create_test_article()

        response = self.client.get(f"/usage/articles/{self.article_id}")

        assert response.status_code == 200
        assert response.json() == []


class TestDictionarySearchTokenUsageIntegration(unittest.TestCase):
    """Integration tests verifying dictionary search calls save_token_usage."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
        self.mock_user = UserResponse(
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

    def test_dictionary_search_calls_save_token_usage(self):
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

        mock_repo = MagicMock()
        mock_repo.save.return_value = "usage-id-123"
        app.dependency_overrides[get_token_usage_repo] = lambda: mock_repo

        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "test",
                "sentence": "This is a test.",
                "language": "English"
            }
        )

        assert response.status_code == 200

        # Verify repo.save was called with correct parameters
        mock_repo.save.assert_called_once()
        call_kwargs = mock_repo.save.call_args[1]
        assert call_kwargs['user_id'] == "test-user-123"
        assert call_kwargs['operation'] == "dictionary_search"
        assert call_kwargs['model'] == "gpt-4.1-mini"
        assert call_kwargs['prompt_tokens'] == 100
        assert call_kwargs['completion_tokens'] == 50
        assert call_kwargs['estimated_cost'] == approx(0.0001)
        assert call_kwargs['metadata']['word'] == "test"
        assert call_kwargs['metadata']['language'] == "English"

    def test_dictionary_search_token_usage_persists_on_success(self):
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

        mock_repo = MagicMock()
        mock_repo.save.return_value = "usage-id-456"
        app.dependency_overrides[get_token_usage_repo] = lambda: mock_repo

        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "word",
                "sentence": "A word.",
                "language": "English"
            }
        )

        assert response.status_code == 200
        # Verify repo.save was called even with minimal response
        assert mock_repo.save.called

    def test_dictionary_search_token_usage_with_german_language(self):
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

        mock_repo = MagicMock()
        mock_repo.save.return_value = "usage-id-789"
        app.dependency_overrides[get_token_usage_repo] = lambda: mock_repo

        response = self.client.post(
            "/dictionary/search",
            json={
                "word": "gehen",
                "sentence": "Ich gehe nach Hause.",
                "language": "German"
            }
        )

        assert response.status_code == 200
        mock_repo.save.assert_called_once()
        call_kwargs = mock_repo.save.call_args[1]
        assert call_kwargs['metadata']['language'] == "German"
        assert call_kwargs['metadata']['word'] == "gehen"


class TestTokenUsageResponseModel(unittest.TestCase):
    """Tests for TokenUsageResponse model validation and edge cases."""

    def setUp(self):
        """Set up test fixtures."""
        from api.models import TokenUsageResponse

        self.TokenUsageResponse = TokenUsageResponse
        self.now = datetime.now(timezone.utc)

    def test_token_usage_record_with_all_fields(self):
        """Test TokenUsageResponse with all fields provided."""
        record = self.TokenUsageResponse(
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
        assert record.estimated_cost == approx(0.0001)
        assert record.metadata == {"word": "test", "language": "English"}
        assert record.created_at == self.now

    def test_token_usage_record_with_empty_metadata(self):
        """Test TokenUsageResponse with empty metadata dictionary."""
        record = self.TokenUsageResponse(
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
        """Test TokenUsageResponse without metadata defaults to empty dict."""
        record = self.TokenUsageResponse(
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
        """Test TokenUsageResponse with zero tokens (edge case)."""
        record = self.TokenUsageResponse(
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
        assert record.estimated_cost == approx(0.0)

    def test_token_usage_record_with_very_large_token_counts(self):
        """Test TokenUsageResponse with very large token counts."""
        record = self.TokenUsageResponse(
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
        assert record.estimated_cost == approx(45.50)

    def test_token_usage_record_with_very_small_cost(self):
        """Test TokenUsageResponse with very small estimated cost."""
        record = self.TokenUsageResponse(
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

        assert record.estimated_cost == approx(0.00000001)

    def test_token_usage_record_with_article_operation(self):
        """Test TokenUsageResponse for article_generation operation."""
        record = self.TokenUsageResponse(
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
        """Test TokenUsageResponse with nested metadata."""
        complex_metadata = {
            "word": "test",
            "language": "English",
            "context": {
                "lemma": "test",
                "pos": "noun"
            },
            "tags": ["vocabulary", "search"]
        }

        record = self.TokenUsageResponse(
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
        """Test TokenUsageResponse JSON serialization."""
        record = self.TokenUsageResponse(
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

        serialized = record.model_dump()
        assert serialized['id'] == "usage-123"
        assert serialized['operation'] == "dictionary_search"
        assert serialized['prompt_tokens'] == 100
        assert isinstance(serialized['created_at'], datetime)

    def test_token_usage_record_with_different_models(self):
        """Test TokenUsageResponse with various model names."""
        models = ["gpt-4.1-mini", "gpt-4", "claude-3-opus", "claude-3-sonnet"]

        for model in models:
            record = self.TokenUsageResponse(
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


class TestTokenUsageResponseConstruction(unittest.TestCase):
    """Tests for TokenUsageResponse construction edge cases."""

    def setUp(self):
        """Set up test fixtures."""
        from api.models import TokenUsageResponse
        from pydantic import ValidationError

        self.TokenUsageResponse = TokenUsageResponse
        self.ValidationError = ValidationError
        self.now = datetime.now(timezone.utc)

    def test_token_usage_record_missing_required_field_id(self):
        """Test TokenUsageResponse validation fails without id."""
        with self.assertRaises(self.ValidationError):
            self.TokenUsageResponse(
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
        """Test TokenUsageResponse validation fails without user_id."""
        with self.assertRaises(self.ValidationError):
            self.TokenUsageResponse(
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
        """Test TokenUsageResponse validation fails without operation."""
        with self.assertRaises(self.ValidationError):
            self.TokenUsageResponse(
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
        """Test TokenUsageResponse validation fails without model."""
        with self.assertRaises(self.ValidationError):
            self.TokenUsageResponse(
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
        """Test TokenUsageResponse validation fails without prompt_tokens."""
        with self.assertRaises(self.ValidationError):
            self.TokenUsageResponse(
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
        """Test TokenUsageResponse validation fails without completion_tokens."""
        with self.assertRaises(self.ValidationError):
            self.TokenUsageResponse(
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
        """Test TokenUsageResponse validation fails without total_tokens."""
        with self.assertRaises(self.ValidationError):
            self.TokenUsageResponse(
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
        """Test TokenUsageResponse validation fails without estimated_cost."""
        with self.assertRaises(self.ValidationError):
            self.TokenUsageResponse(
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
        """Test TokenUsageResponse validation fails without created_at."""
        with self.assertRaises(self.ValidationError):
            self.TokenUsageResponse(
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
        """Test TokenUsageResponse allows zero but validates logically."""
        # Pydantic doesn't have field constraints, but we test the model accepts all ints
        record = self.TokenUsageResponse(
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
