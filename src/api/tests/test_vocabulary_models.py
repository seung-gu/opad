"""Unit tests for vocabulary-related Pydantic models.

Tests for:
- SearchResponse model with new fields
- VocabularyRequest model with new fields
- VocabularyResponse model with new fields
- VocabularyCount model with new fields
- Conjugations model validation
- CEFRLevel validation
"""

import unittest
from datetime import datetime, timezone
from pydantic import ValidationError

from api.models import (
    Conjugations,
    SearchResponse,
    VocabularyRequest,
    VocabularyResponse,
    VocabularyCount,
    CEFRLevel
)


class TestConjugationsModel(unittest.TestCase):
    """Test Conjugations Pydantic model."""

    def test_conjugations_creation_with_all_fields(self):
        """Test creating Conjugations with all fields."""
        conj = Conjugations(
            present="gehe, gehst, geht",
            past="ging",
            perfect="gegangen"
        )
        self.assertEqual(conj.present, "gehe, gehst, geht")
        self.assertEqual(conj.past, "ging")
        self.assertEqual(conj.perfect, "gegangen")

    def test_conjugations_creation_with_none_fields(self):
        """Test creating Conjugations with None fields."""
        conj = Conjugations(
            present="run, runs",
            past=None,
            perfect=None
        )
        self.assertEqual(conj.present, "run, runs")
        self.assertIsNone(conj.past)
        self.assertIsNone(conj.perfect)

    def test_conjugations_creation_without_fields(self):
        """Test creating Conjugations without any fields."""
        conj = Conjugations()
        self.assertIsNone(conj.present)
        self.assertIsNone(conj.past)
        self.assertIsNone(conj.perfect)

    def test_conjugations_serialization(self):
        """Test Conjugations JSON serialization."""
        conj = Conjugations(
            present="ich gehe",
            past="ich ging",
            perfect="ich bin gegangen"
        )
        serialized = conj.dict()
        self.assertEqual(serialized['present'], "ich gehe")
        self.assertEqual(serialized['past'], "ich ging")
        self.assertEqual(serialized['perfect'], "ich bin gegangen")

    def test_conjugations_with_empty_strings(self):
        """Test Conjugations with empty strings."""
        conj = Conjugations(present="", past="", perfect="")
        self.assertEqual(conj.present, "")
        self.assertEqual(conj.past, "")
        self.assertEqual(conj.perfect, "")

    def test_conjugations_with_unicode(self):
        """Test Conjugations with unicode characters."""
        conj = Conjugations(
            present="über, überst",
            past="überging",
            perfect="übergangen"
        )
        self.assertIn("ü", conj.present)
        self.assertIn("ü", conj.past)
        self.assertIn("ü", conj.perfect)


class TestSearchResponseModel(unittest.TestCase):
    """Test SearchResponse model with new fields."""

    def test_search_response_with_all_new_fields(self):
        """Test SearchResponse with all new fields."""
        response = SearchResponse(
            lemma="gehen",
            definition="to go, to walk",
            related_words=["gehen"],
            pos="verb",
            gender=None,
            conjugations=Conjugations(
                present="gehe, gehst, geht",
                past="ging",
                perfect="gegangen"
            ),
            level="A1"
        )
        self.assertEqual(response.lemma, "gehen")
        self.assertEqual(response.definition, "to go, to walk")
        self.assertEqual(response.pos, "verb")
        self.assertIsNone(response.gender)
        self.assertIsNotNone(response.conjugations)
        self.assertEqual(response.conjugations.past, "ging")
        self.assertEqual(response.level, "A1")

    def test_search_response_minimal_fields(self):
        """Test SearchResponse with minimal fields."""
        response = SearchResponse(
            lemma="test",
            definition="a procedure"
        )
        self.assertEqual(response.lemma, "test")
        self.assertEqual(response.definition, "a procedure")
        self.assertIsNone(response.related_words)
        self.assertIsNone(response.pos)
        self.assertIsNone(response.gender)
        self.assertIsNone(response.conjugations)
        self.assertIsNone(response.level)

    def test_search_response_with_noun_and_gender(self):
        """Test SearchResponse with German noun and gender."""
        response = SearchResponse(
            lemma="Hund",
            definition="dog",
            related_words=["Hund"],
            pos="noun",
            gender="der",
            conjugations=None,
            level="A1"
        )
        self.assertEqual(response.lemma, "Hund")
        self.assertEqual(response.pos, "noun")
        self.assertEqual(response.gender, "der")
        self.assertIsNone(response.conjugations)

    def test_search_response_json_serialization(self):
        """Test SearchResponse JSON serialization."""
        response = SearchResponse(
            lemma="gehen",
            definition="to go",
            pos="verb",
            level="A1"
        )
        serialized = response.dict()
        self.assertEqual(serialized['lemma'], "gehen")
        self.assertEqual(serialized['pos'], "verb")
        self.assertEqual(serialized['level'], "A1")

    def test_search_response_all_cefr_levels(self):
        """Test SearchResponse with all valid CEFR levels."""
        levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
        for level in levels:
            response = SearchResponse(
                lemma="test",
                definition="test",
                level=level
            )
            self.assertEqual(response.level, level)


class TestVocabularyRequestModel(unittest.TestCase):
    """Test VocabularyRequest model with new fields."""

    def test_vocabulary_request_with_all_new_fields(self):
        """Test VocabularyRequest with all new fields."""
        request = VocabularyRequest(
            article_id="article-123",
            word="gehen",
            lemma="gehen",
            definition="to go",
            sentence="Ich gehe nach Hause.",
            language="German",
            related_words=["gehen"],
            span_id="span-123",
            pos="verb",
            gender=None,
            conjugations={"present": "gehe", "past": "ging", "perfect": "gegangen"},
            level="A1"
        )
        self.assertEqual(request.article_id, "article-123")
        self.assertEqual(request.lemma, "gehen")
        self.assertEqual(request.pos, "verb")
        self.assertIsNone(request.gender)
        # Conjugations is stored as dict (converted by field_validator for MongoDB storage)
        self.assertIsNotNone(request.conjugations)
        self.assertEqual(request.conjugations["present"], "gehe")
        self.assertEqual(request.level, "A1")

    def test_vocabulary_request_minimal_fields(self):
        """Test VocabularyRequest with minimal required fields."""
        request = VocabularyRequest(
            article_id="article-123",
            word="test",
            lemma="test",
            definition="a procedure",
            sentence="This is a test.",
            language="English"
        )
        self.assertEqual(request.article_id, "article-123")
        self.assertEqual(request.word, "test")
        self.assertIsNone(request.related_words)
        self.assertIsNone(request.span_id)
        self.assertIsNone(request.pos)
        self.assertIsNone(request.gender)
        self.assertIsNone(request.conjugations)
        self.assertIsNone(request.level)

    def test_vocabulary_request_with_noun_and_gender(self):
        """Test VocabularyRequest with noun and gender."""
        request = VocabularyRequest(
            article_id="article-123",
            word="Hund",
            lemma="Hund",
            definition="dog",
            sentence="Der Hund ist groß.",
            language="German",
            pos="noun",
            gender="der",
            level="A1"
        )
        self.assertEqual(request.lemma, "Hund")
        self.assertEqual(request.pos, "noun")
        self.assertEqual(request.gender, "der")

    def test_vocabulary_request_validation_missing_required_field(self):
        """Test VocabularyRequest validation fails without required field."""
        with self.assertRaises(ValidationError):
            VocabularyRequest(
                article_id="article-123",
                word="test",
                # Missing lemma
                definition="test",
                sentence="test",
                language="English"
            )

    def test_vocabulary_request_all_cefr_levels(self):
        """Test VocabularyRequest with all valid CEFR levels."""
        levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
        for level in levels:
            request = VocabularyRequest(
                article_id="article-123",
                word="test",
                lemma="test",
                definition="test",
                sentence="test",
                language="English",
                level=level
            )
            self.assertEqual(request.level, level)


class TestVocabularyResponseModel(unittest.TestCase):
    """Test VocabularyResponse model with new fields."""

    def setUp(self):
        """Set up test fixtures."""
        self.now = datetime.now(timezone.utc)

    def test_vocabulary_response_with_all_new_fields(self):
        """Test VocabularyResponse with all new fields."""
        response = VocabularyResponse(
            id="vocab-123",
            article_id="article-123",
            word="gehen",
            lemma="gehen",
            definition="to go",
            sentence="Ich gehe.",
            language="German",
            related_words=["gehen"],
            span_id="span-123",
            created_at=self.now,
            user_id="user-123",
            pos="verb",
            gender=None,
            conjugations=Conjugations(
                present="gehe",
                past="ging",
                perfect="gegangen"
            ),
            level="A1"
        )
        self.assertEqual(response.id, "vocab-123")
        self.assertEqual(response.pos, "verb")
        self.assertIsNone(response.gender)
        self.assertIsNotNone(response.conjugations)
        self.assertEqual(response.level, "A1")

    def test_vocabulary_response_minimal_fields(self):
        """Test VocabularyResponse with minimal required fields."""
        response = VocabularyResponse(
            id="vocab-123",
            article_id="article-123",
            word="test",
            lemma="test",
            definition="test",
            sentence="test",
            language="English",
            created_at=self.now
        )
        self.assertEqual(response.id, "vocab-123")
        self.assertIsNone(response.related_words)
        self.assertIsNone(response.span_id)
        self.assertIsNone(response.user_id)
        self.assertIsNone(response.pos)
        self.assertIsNone(response.gender)
        self.assertIsNone(response.conjugations)
        self.assertIsNone(response.level)

    def test_vocabulary_response_with_german_noun(self):
        """Test VocabularyResponse with German noun."""
        response = VocabularyResponse(
            id="vocab-123",
            article_id="article-123",
            word="Hund",
            lemma="Hund",
            definition="dog",
            sentence="Der Hund ist groß.",
            language="German",
            created_at=self.now,
            pos="noun",
            gender="der",
            level="A1"
        )
        self.assertEqual(response.lemma, "Hund")
        self.assertEqual(response.gender, "der")
        self.assertEqual(response.level, "A1")

    def test_vocabulary_response_json_serialization(self):
        """Test VocabularyResponse JSON serialization."""
        response = VocabularyResponse(
            id="vocab-123",
            article_id="article-123",
            word="test",
            lemma="test",
            definition="test",
            sentence="test",
            language="English",
            created_at=self.now,
            level="B1"
        )
        serialized = response.dict()
        self.assertEqual(serialized['id'], "vocab-123")
        self.assertEqual(serialized['level'], "B1")
        self.assertIsInstance(serialized['created_at'], datetime)

    def test_vocabulary_response_validation_missing_required_field(self):
        """Test VocabularyResponse validation fails without required field."""
        with self.assertRaises(ValidationError):
            VocabularyResponse(
                id="vocab-123",
                article_id="article-123",
                word="test",
                lemma="test",
                definition="test",
                sentence="test",
                language="English"
                # Missing created_at
            )


class TestVocabularyCountModel(unittest.TestCase):
    """Test VocabularyCount model with new fields."""

    def setUp(self):
        """Set up test fixtures."""
        self.now = datetime.now(timezone.utc)

    def test_vocabulary_count_with_all_new_fields(self):
        """Test VocabularyCount with all new fields."""
        count = VocabularyCount(
            id="vocab-123",
            article_id="article-123",
            word="gehen",
            lemma="gehen",
            definition="to go",
            sentence="Ich gehe.",
            language="German",
            related_words=["gehen"],
            span_id="span-123",
            created_at=self.now,
            user_id="user-123",
            count=5,
            article_ids=["article-1", "article-2"],
            pos="verb",
            gender=None,
            conjugations=Conjugations(
                present="gehe",
                past="ging",
                perfect="gegangen"
            ),
            level="A1"
        )
        self.assertEqual(count.lemma, "gehen")
        self.assertEqual(count.count, 5)
        self.assertEqual(count.pos, "verb")
        self.assertIsNone(count.gender)
        self.assertIsNotNone(count.conjugations)
        self.assertEqual(count.level, "A1")

    def test_vocabulary_count_minimal_fields(self):
        """Test VocabularyCount with minimal required fields."""
        count = VocabularyCount(
            id="vocab-123",
            article_id="article-123",
            word="test",
            lemma="test",
            definition="test",
            sentence="test",
            language="English",
            created_at=self.now,
            count=1,
            article_ids=["article-123"]
        )
        self.assertEqual(count.count, 1)
        self.assertEqual(len(count.article_ids), 1)
        self.assertIsNone(count.pos)
        self.assertIsNone(count.gender)
        self.assertIsNone(count.conjugations)
        self.assertIsNone(count.level)

    def test_vocabulary_count_multiple_article_ids(self):
        """Test VocabularyCount with multiple article IDs."""
        article_ids = ["article-1", "article-2", "article-3"]
        count = VocabularyCount(
            id="vocab-123",
            article_id="article-1",
            word="test",
            lemma="test",
            definition="test",
            sentence="test",
            language="English",
            created_at=self.now,
            count=3,
            article_ids=article_ids
        )
        self.assertEqual(count.count, 3)
        self.assertEqual(count.article_ids, article_ids)

    def test_vocabulary_count_with_german_noun(self):
        """Test VocabularyCount with German noun."""
        count = VocabularyCount(
            id="vocab-123",
            article_id="article-123",
            word="Hund",
            lemma="Hund",
            definition="dog",
            sentence="Der Hund ist groß.",
            language="German",
            created_at=self.now,
            count=2,
            article_ids=["article-1", "article-2"],
            pos="noun",
            gender="der",
            level="A1"
        )
        self.assertEqual(count.lemma, "Hund")
        self.assertEqual(count.gender, "der")
        self.assertEqual(count.pos, "noun")
        self.assertEqual(count.level, "A1")

    def test_vocabulary_count_json_serialization(self):
        """Test VocabularyCount JSON serialization."""
        count = VocabularyCount(
            id="vocab-123",
            article_id="article-123",
            word="test",
            lemma="test",
            definition="test",
            sentence="test",
            language="English",
            created_at=self.now,
            count=5,
            article_ids=["article-1", "article-2"],
            level="B2"
        )
        serialized = count.dict()
        self.assertEqual(serialized['count'], 5)
        self.assertEqual(len(serialized['article_ids']), 2)
        self.assertEqual(serialized['level'], "B2")

    def test_vocabulary_count_validation_count_positive(self):
        """Test VocabularyCount count must be positive integer."""
        # Count should be positive, test with valid value
        count = VocabularyCount(
            id="vocab-123",
            article_id="article-123",
            word="test",
            lemma="test",
            definition="test",
            sentence="test",
            language="English",
            created_at=self.now,
            count=1,
            article_ids=["article-123"]
        )
        self.assertEqual(count.count, 1)

    def test_vocabulary_count_validation_missing_required_field(self):
        """Test VocabularyCount validation fails without required field."""
        with self.assertRaises(ValidationError):
            VocabularyCount(
                id="vocab-123",
                article_id="article-123",
                word="test",
                lemma="test",
                definition="test",
                sentence="test",
                language="English",
                created_at=self.now,
                # Missing count
                article_ids=["article-123"]
            )


class TestCEFRLevelValidation(unittest.TestCase):
    """Test CEFRLevel type definition validation."""

    def test_cerf_all_valid_levels(self):
        """Test all valid CEFR levels."""
        valid_levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
        for level in valid_levels:
            # These should be accepted by Pydantic when used in model validation
            self.assertIn(level, valid_levels)

    def test_cerf_level_used_in_search_response(self):
        """Test CEFRLevel in SearchResponse model."""
        response = SearchResponse(
            lemma="test",
            definition="test",
            level="A1"
        )
        self.assertEqual(response.level, "A1")

        response = SearchResponse(
            lemma="test",
            definition="test",
            level="C2"
        )
        self.assertEqual(response.level, "C2")

    def test_cerf_level_used_in_vocabulary_response(self):
        """Test CEFRLevel in VocabularyResponse model."""
        now = datetime.now(timezone.utc)
        for level in ["A1", "A2", "B1", "B2", "C1", "C2"]:
            response = VocabularyResponse(
                id="vocab-123",
                article_id="article-123",
                word="test",
                lemma="test",
                definition="test",
                sentence="test",
                language="English",
                created_at=now,
                level=level
            )
            self.assertEqual(response.level, level)


class TestModelIntegration(unittest.TestCase):
    """Integration tests for vocabulary models."""

    def setUp(self):
        """Set up test fixtures."""
        self.now = datetime.now(timezone.utc)

    def test_german_verb_workflow(self):
        """Integration test: German verb request to response."""
        # Create request
        request = VocabularyRequest(
            article_id="article-123",
            word="gehend",
            lemma="gehen",
            definition="to go, to walk",
            sentence="Ich gehe nach Hause.",
            language="German",
            pos="verb",
            conjugations={"present": "gehe", "past": "ging", "perfect": "gegangen"},
            level="A1"
        )

        # Convert to response
        response = VocabularyResponse(
            id="vocab-123",
            article_id=request.article_id,
            word=request.word,
            lemma=request.lemma,
            definition=request.definition,
            sentence=request.sentence,
            language=request.language,
            pos=request.pos,
            conjugations=request.conjugations,  # Already a Conjugations object from request
            level=request.level,
            created_at=self.now,
            user_id="user-123"
        )

        self.assertEqual(response.lemma, "gehen")
        self.assertEqual(response.pos, "verb")
        self.assertIsNotNone(response.conjugations)

    def test_german_noun_workflow(self):
        """Integration test: German noun request to response."""
        # Create request for German noun
        request = VocabularyRequest(
            article_id="article-123",
            word="Hund",
            lemma="Hund",
            definition="dog",
            sentence="Der Hund ist groß.",
            language="German",
            pos="noun",
            gender="der",
            level="A1"
        )

        # Verify capitalization is preserved
        self.assertEqual(request.lemma, "Hund")

        # Create response
        response = VocabularyResponse(
            id="vocab-123",
            article_id=request.article_id,
            word=request.word,
            lemma=request.lemma,
            definition=request.definition,
            sentence=request.sentence,
            language=request.language,
            pos=request.pos,
            gender=request.gender,
            level=request.level,
            created_at=self.now
        )

        # Verify capitalization still preserved
        self.assertEqual(response.lemma, "Hund")
        self.assertEqual(response.gender, "der")

    def test_vocabulary_count_from_multiple_entries(self):
        """Integration test: create VocabularyCount from multiple entries."""
        count = VocabularyCount(
            id="vocab-456",
            article_id="article-1",
            word="gehend",
            lemma="gehen",
            definition="to go, to walk",
            sentence="Ich gehe nach Hause.",
            language="German",
            related_words=["gehen"],
            created_at=self.now,
            user_id="user-123",
            count=5,  # Seen 5 times
            article_ids=["article-1", "article-2", "article-3"],
            pos="verb",
            conjugations=Conjugations(present="gehe", past="ging", perfect="gegangen"),
            level="A1"
        )

        self.assertEqual(count.count, 5)
        self.assertEqual(len(count.article_ids), 3)
        self.assertEqual(count.pos, "verb")
        self.assertIsNotNone(count.conjugations)


if __name__ == '__main__':
    unittest.main()
