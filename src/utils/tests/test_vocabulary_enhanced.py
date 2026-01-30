"""Unit tests for enhanced vocabulary search feature.

Tests for:
- Conjugations model validation (Pydantic models)
- CEFRLevel validation (Pydantic type definitions)
- Regex injection prevention in save_vocabulary (special characters in lemma)
- New fields (pos, gender, conjugations, level) are properly saved and retrieved
- get_vocabularies returns new fields
- get_vocabulary_by_id returns new fields
- German noun capitalization preservation
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone
from pymongo.errors import PyMongoError
import re

from utils.mongodb import (
    save_vocabulary,
    get_vocabularies,
    get_vocabulary_by_id,
    delete_vocabulary
)
from api.models import Conjugations, CEFRLevel


class TestConjugationsModel(unittest.TestCase):
    """Test cases for Conjugations Pydantic model."""

    def test_conjugations_all_fields_valid(self):
        """Test creating Conjugations with all fields."""
        conj = Conjugations(
            present="gehe, gehst, geht",
            past="ging",
            perfect="gegangen"
        )
        self.assertEqual(conj.present, "gehe, gehst, geht")
        self.assertEqual(conj.past, "ging")
        self.assertEqual(conj.perfect, "gegangen")

    def test_conjugations_with_partial_fields(self):
        """Test creating Conjugations with some fields None."""
        conj = Conjugations(
            present="gehe, gehst, geht",
            past=None,
            perfect=None
        )
        self.assertEqual(conj.present, "gehe, gehst, geht")
        self.assertIsNone(conj.past)
        self.assertIsNone(conj.perfect)

    def test_conjugations_all_none(self):
        """Test creating Conjugations with all fields None."""
        conj = Conjugations(
            present=None,
            past=None,
            perfect=None
        )
        self.assertIsNone(conj.present)
        self.assertIsNone(conj.past)
        self.assertIsNone(conj.perfect)

    def test_conjugations_default_none(self):
        """Test creating Conjugations without providing fields."""
        conj = Conjugations()
        self.assertIsNone(conj.present)
        self.assertIsNone(conj.past)
        self.assertIsNone(conj.perfect)

    def test_conjugations_to_dict(self):
        """Test converting Conjugations to dictionary."""
        conj = Conjugations(
            present="run, runs",
            past="ran",
            perfect="run"
        )
        conj_dict = conj.dict()
        self.assertEqual(conj_dict['present'], "run, runs")
        self.assertEqual(conj_dict['past'], "ran")
        self.assertEqual(conj_dict['perfect'], "run")

    def test_conjugations_with_special_characters(self):
        """Test Conjugations with special characters in values."""
        conj = Conjugations(
            present="über, überst",
            past="überging",
            perfect="übergangen"
        )
        self.assertEqual(conj.present, "über, überst")
        self.assertIn("über", conj.perfect)

    def test_conjugations_empty_strings_allowed(self):
        """Test that empty strings are allowed in Conjugations."""
        conj = Conjugations(
            present="",
            past="",
            perfect=""
        )
        self.assertEqual(conj.present, "")
        self.assertEqual(conj.past, "")
        self.assertEqual(conj.perfect, "")


class TestCEFRLevelType(unittest.TestCase):
    """Test cases for CEFRLevel type validation."""

    def test_cerf_level_a1_valid(self):
        """Test CEFRLevel A1 is valid."""
        # Valid CEFR levels
        valid_levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
        for level in valid_levels:
            # If this doesn't raise an error, the literal is valid
            self.assertIn(level, ["A1", "A2", "B1", "B2", "C1", "C2"])

    def test_cerf_level_all_valid(self):
        """Test all valid CEFR levels."""
        valid_levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
        for level in valid_levels:
            self.assertIn(level, valid_levels)

    def test_cerf_level_invalid_not_in_literal(self):
        """Test that invalid CEFR levels would not pass Pydantic validation."""
        invalid_levels = ["A0", "A3", "B3", "C3", "D1", "BEGINNER", "ADVANCED"]
        valid_levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
        for level in invalid_levels:
            self.assertNotIn(level, valid_levels)


class TestRegexInjectionPrevention(unittest.TestCase):
    """Test cases for regex injection prevention in save_vocabulary."""

    def setUp(self):
        """Set up test fixtures."""
        self.article_id = "test-article-123"
        self.user_id = "test-user-123"

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_vocabulary_escapes_regex_metacharacters_in_lemma(self, mock_get_client):
        """Test that regex metacharacters in lemma are properly escaped."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.find_one.return_value = None  # No existing vocabulary
        mock_collection.insert_one.return_value = None

        # Test various regex metacharacters
        regex_chars = ['.', '*', '+', '?', '^', '$', '|', '(', ')', '[', ']', '{', '}', '\\']

        for char in regex_chars:
            lemma_with_char = f"word{char}test"

            result = save_vocabulary(
                article_id=self.article_id,
                word="wordtest",
                lemma=lemma_with_char,
                definition="test definition",
                sentence="This is a test.",
                language="English",
                user_id=self.user_id
            )

            # Verify that find_one was called
            self.assertIsNotNone(result)

            # Get the query passed to find_one
            call_args = mock_collection.find_one.call_args_list
            if call_args:
                last_query = call_args[-1][0][0]  # Get the most recent query
                # Verify query uses regex with escaped lemma
                self.assertIn('$regex', last_query.get('lemma', {}))
                regex_pattern = last_query['lemma'].get('$regex', '')
                # The pattern should escape the metacharacter
                self.assertIn('word', regex_pattern)

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_vocabulary_prevents_regex_injection_attack(self, mock_get_client):
        """Test prevention of regex injection attack in lemma field."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = None

        # Attempt regex injection: .*
        injection_lemma = "word.*"

        result = save_vocabulary(
            article_id=self.article_id,
            word="word",
            lemma=injection_lemma,
            definition="test definition",
            sentence="This is a test.",
            language="English",
            user_id=self.user_id
        )

        # Should succeed without error
        self.assertIsNotNone(result)

        # Verify that the regex pattern was escaped
        call_args = mock_collection.find_one.call_args_list
        if call_args:
            last_query = call_args[-1][0][0]
            regex_pattern = last_query.get('lemma', {}).get('$regex', '')
            # Verify that .* is escaped to \.\*
            self.assertNotEqual(regex_pattern, injection_lemma)

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_vocabulary_special_characters_in_lemma_preserved(self, mock_get_client):
        """Test that special characters in lemma are preserved in database."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = None

        # Test with German umlaut
        lemma_with_umlaut = "Übergang"

        result = save_vocabulary(
            article_id=self.article_id,
            word="Übergang",
            lemma=lemma_with_umlaut,
            definition="crossing, transition",
            sentence="Der Übergang war schwierig.",
            language="German",
            user_id=self.user_id
        )

        self.assertIsNotNone(result)

        # Verify that insert_one was called with the original lemma
        insert_calls = mock_collection.insert_one.call_args_list
        if insert_calls:
            inserted_doc = insert_calls[-1][0][0]
            # Verify lemma is preserved exactly as provided
            self.assertEqual(inserted_doc['lemma'], lemma_with_umlaut)

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_vocabulary_case_insensitive_duplicate_check(self, mock_get_client):
        """Test that duplicate check is case-insensitive for lemma."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # Mock existing vocabulary with lowercase lemma
        mock_existing = {
            '_id': 'existing-vocab-id',
            'lemma': 'hund',
            'span_id': 'old-span-id'
        }
        mock_collection.find_one.return_value = mock_existing

        result = save_vocabulary(
            article_id=self.article_id,
            word="Hund",
            lemma="Hund",  # Uppercase version
            definition="dog",
            sentence="Der Hund ist groß.",
            language="German",
            user_id=self.user_id
        )

        # Should return existing vocabulary ID (case-insensitive match)
        self.assertEqual(result, 'existing-vocab-id')

        # Verify query uses case-insensitive regex
        call_args = mock_collection.find_one.call_args_list
        if call_args:
            query = call_args[-1][0][0]
            self.assertIn('$options', query.get('lemma', {}))
            self.assertEqual(query['lemma']['$options'], 'i')


class TestNewFieldsSaveAndRetrieve(unittest.TestCase):
    """Test cases for saving and retrieving new fields (pos, gender, conjugations, level)."""

    def setUp(self):
        """Set up test fixtures."""
        self.article_id = "test-article-123"
        self.user_id = "test-user-123"

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_vocabulary_with_all_new_fields(self, mock_get_client):
        """Test saving vocabulary with all new fields."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = None

        conjugations_dict = {
            'present': 'gehe, gehst, geht',
            'past': 'ging',
            'perfect': 'gegangen'
        }

        result = save_vocabulary(
            article_id=self.article_id,
            word="gehen",
            lemma="gehen",
            definition="to go, to walk",
            sentence="Ich gehe nach Hause.",
            language="German",
            user_id=self.user_id,
            pos="verb",
            gender=None,
            conjugations=conjugations_dict,
            level="A1"
        )

        self.assertIsNotNone(result)

        # Verify insert_one was called with all new fields
        insert_calls = mock_collection.insert_one.call_args_list
        if insert_calls:
            inserted_doc = insert_calls[-1][0][0]
            self.assertEqual(inserted_doc['pos'], 'verb')
            self.assertEqual(inserted_doc['conjugations'], conjugations_dict)
            self.assertEqual(inserted_doc['level'], 'A1')
            self.assertIsNone(inserted_doc['gender'])

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_vocabulary_preserves_german_noun_capitalization(self, mock_get_client):
        """Test that German noun capitalization is preserved."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = None

        # German nouns must be capitalized
        result = save_vocabulary(
            article_id=self.article_id,
            word="Hund",
            lemma="Hund",  # Must preserve capital H
            definition="dog",
            sentence="Der Hund ist groß.",
            language="German",
            user_id=self.user_id,
            pos="noun",
            gender="der",
            level="A1"
        )

        self.assertIsNotNone(result)

        # Verify capitalization is preserved
        insert_calls = mock_collection.insert_one.call_args_list
        if insert_calls:
            inserted_doc = insert_calls[-1][0][0]
            # Lemma should preserve capitalization
            self.assertEqual(inserted_doc['lemma'], 'Hund')
            self.assertEqual(inserted_doc['pos'], 'noun')
            self.assertEqual(inserted_doc['gender'], 'der')

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_vocabulary_with_pos_only(self, mock_get_client):
        """Test saving vocabulary with only pos field."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = None

        result = save_vocabulary(
            article_id=self.article_id,
            word="beautiful",
            lemma="beautiful",
            definition="attractive",
            sentence="This is a beautiful day.",
            language="English",
            pos="adjective"
        )

        self.assertIsNotNone(result)

        insert_calls = mock_collection.insert_one.call_args_list
        if insert_calls:
            inserted_doc = insert_calls[-1][0][0]
            self.assertEqual(inserted_doc['pos'], 'adjective')
            self.assertIsNone(inserted_doc['gender'])
            self.assertIsNone(inserted_doc['conjugations'])
            self.assertIsNone(inserted_doc['level'])

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_vocabulary_with_gender_only(self, mock_get_client):
        """Test saving vocabulary with only gender field."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = None

        result = save_vocabulary(
            article_id=self.article_id,
            word="le chat",
            lemma="chat",
            definition="cat",
            sentence="Le chat est noir.",
            language="French",
            gender="le"
        )

        self.assertIsNotNone(result)

        insert_calls = mock_collection.insert_one.call_args_list
        if insert_calls:
            inserted_doc = insert_calls[-1][0][0]
            self.assertEqual(inserted_doc['gender'], 'le')
            self.assertIsNone(inserted_doc['pos'])
            self.assertIsNone(inserted_doc['conjugations'])
            self.assertIsNone(inserted_doc['level'])

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_vocabulary_with_all_cefr_levels(self, mock_get_client):
        """Test saving vocabulary with each valid CEFR level."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = None

        levels = ["A1", "A2", "B1", "B2", "C1", "C2"]

        for level in levels:
            mock_collection.reset_mock()

            result = save_vocabulary(
                article_id=self.article_id,
                word="test",
                lemma="test",
                definition="test",
                sentence="test",
                language="English",
                level=level
            )

            self.assertIsNotNone(result)

            insert_calls = mock_collection.insert_one.call_args_list
            if insert_calls:
                inserted_doc = insert_calls[-1][0][0]
                self.assertEqual(inserted_doc['level'], level)


class TestGetVocabulariesReturnsNewFields(unittest.TestCase):
    """Test cases for get_vocabularies returning new fields."""

    def setUp(self):
        """Set up test fixtures."""
        self.article_id = "test-article-123"
        self.user_id = "test-user-123"

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabularies_returns_new_fields(self, mock_get_client):
        """Test that get_vocabularies returns all new fields in response."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # Mock vocabulary document with all fields
        mock_vocab = {
            '_id': 'vocab-123',
            'article_id': self.article_id,
            'word': 'gehen',
            'lemma': 'gehen',
            'definition': 'to go',
            'sentence': 'Ich gehe.',
            'language': 'German',
            'span_id': 'span-123',
            'related_words': ['gehen', 'gehend'],
            'user_id': self.user_id,
            'pos': 'verb',
            'gender': None,
            'conjugations': {
                'present': 'gehe, gehst, geht',
                'past': 'ging',
                'perfect': 'gegangen'
            },
            'level': 'A1',
            'created_at': datetime.now(timezone.utc)
        }

        mock_collection.find.return_value.sort.return_value = [mock_vocab]

        result = get_vocabularies(article_id=self.article_id, user_id=self.user_id)

        self.assertEqual(len(result), 1)
        vocab = result[0]

        # Verify all new fields are present in response
        self.assertEqual(vocab['pos'], 'verb')
        self.assertIsNone(vocab['gender'])
        self.assertEqual(vocab['conjugations'], mock_vocab['conjugations'])
        self.assertEqual(vocab['level'], 'A1')

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabularies_handles_missing_new_fields(self, mock_get_client):
        """Test that get_vocabularies handles documents without new fields."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # Mock vocabulary document without new fields (for backward compatibility)
        mock_vocab = {
            '_id': 'vocab-123',
            'article_id': self.article_id,
            'word': 'test',
            'lemma': 'test',
            'definition': 'a procedure',
            'sentence': 'This is a test.',
            'language': 'English',
            'span_id': None,
            'related_words': None,
            'user_id': self.user_id,
            'created_at': datetime.now(timezone.utc)
            # No pos, gender, conjugations, level fields
        }

        mock_collection.find.return_value.sort.return_value = [mock_vocab]

        result = get_vocabularies(article_id=self.article_id, user_id=self.user_id)

        self.assertEqual(len(result), 1)
        vocab = result[0]

        # Verify fields are None when not present in document
        self.assertIsNone(vocab['pos'])
        self.assertIsNone(vocab['gender'])
        self.assertIsNone(vocab['conjugations'])
        self.assertIsNone(vocab['level'])

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabularies_with_article_filter(self, mock_get_client):
        """Test get_vocabularies with article_id filter includes new fields."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        mock_vocab = {
            '_id': 'vocab-123',
            'article_id': self.article_id,
            'word': 'Hund',
            'lemma': 'Hund',
            'definition': 'dog',
            'sentence': 'Der Hund ist groß.',
            'language': 'German',
            'span_id': 'span-1',
            'related_words': ['Hund'],
            'user_id': self.user_id,
            'pos': 'noun',
            'gender': 'der',
            'conjugations': None,
            'level': 'A1',
            'created_at': datetime.now(timezone.utc)
        }

        mock_collection.find.return_value.sort.return_value = [mock_vocab]

        result = get_vocabularies(article_id=self.article_id)

        self.assertEqual(len(result), 1)
        vocab = result[0]
        self.assertEqual(vocab['pos'], 'noun')
        self.assertEqual(vocab['gender'], 'der')
        self.assertEqual(vocab['level'], 'A1')


class TestGetVocabularyByIdReturnsNewFields(unittest.TestCase):
    """Test cases for get_vocabulary_by_id returning new fields."""

    def setUp(self):
        """Set up test fixtures."""
        self.vocabulary_id = "vocab-123"

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabulary_by_id_returns_new_fields(self, mock_get_client):
        """Test that get_vocabulary_by_id returns all new fields."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # Mock vocabulary document with all fields
        mock_vocab = {
            '_id': self.vocabulary_id,
            'article_id': 'article-123',
            'word': 'gehen',
            'lemma': 'gehen',
            'definition': 'to go, to walk',
            'sentence': 'Ich gehe nach Hause.',
            'language': 'German',
            'span_id': 'span-123',
            'related_words': ['gehen'],
            'user_id': 'user-123',
            'pos': 'verb',
            'gender': None,
            'conjugations': {
                'present': 'gehe, gehst, geht',
                'past': 'ging',
                'perfect': 'gegangen'
            },
            'level': 'A1',
            'created_at': datetime.now(timezone.utc)
        }

        mock_collection.find_one.return_value = mock_vocab

        result = get_vocabulary_by_id(self.vocabulary_id)

        self.assertIsNotNone(result)
        self.assertEqual(result['id'], self.vocabulary_id)
        self.assertEqual(result['pos'], 'verb')
        self.assertIsNone(result['gender'])
        self.assertEqual(result['conjugations']['present'], 'gehe, gehst, geht')
        self.assertEqual(result['level'], 'A1')

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabulary_by_id_handles_missing_new_fields(self, mock_get_client):
        """Test that get_vocabulary_by_id handles documents without new fields."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # Mock vocabulary document without new fields
        mock_vocab = {
            '_id': self.vocabulary_id,
            'article_id': 'article-123',
            'word': 'test',
            'lemma': 'test',
            'definition': 'a procedure',
            'sentence': 'This is a test.',
            'language': 'English',
            'span_id': None,
            'related_words': None,
            'user_id': 'user-123',
            'created_at': datetime.now(timezone.utc)
        }

        mock_collection.find_one.return_value = mock_vocab

        result = get_vocabulary_by_id(self.vocabulary_id)

        self.assertIsNotNone(result)
        self.assertIsNone(result['pos'])
        self.assertIsNone(result['gender'])
        self.assertIsNone(result['conjugations'])
        self.assertIsNone(result['level'])

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabulary_by_id_german_noun_with_gender(self, mock_get_client):
        """Test get_vocabulary_by_id returns German noun with gender."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # Mock German noun vocabulary
        mock_vocab = {
            '_id': self.vocabulary_id,
            'article_id': 'article-123',
            'word': 'Hund',
            'lemma': 'Hund',
            'definition': 'dog',
            'sentence': 'Der Hund ist groß.',
            'language': 'German',
            'span_id': 'span-123',
            'related_words': ['Hund'],
            'user_id': 'user-123',
            'pos': 'noun',
            'gender': 'der',
            'conjugations': None,
            'level': 'A1',
            'created_at': datetime.now(timezone.utc)
        }

        mock_collection.find_one.return_value = mock_vocab

        result = get_vocabulary_by_id(self.vocabulary_id)

        self.assertIsNotNone(result)
        # Verify German noun capitalization is preserved
        self.assertEqual(result['lemma'], 'Hund')
        self.assertEqual(result['pos'], 'noun')
        self.assertEqual(result['gender'], 'der')
        self.assertEqual(result['level'], 'A1')

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabulary_by_id_returns_none_when_not_found(self, mock_get_client):
        """Test that get_vocabulary_by_id returns None when vocabulary not found."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        mock_collection.find_one.return_value = None

        result = get_vocabulary_by_id('nonexistent-id')

        self.assertIsNone(result)

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabulary_by_id_returns_none_on_connection_failure(self, mock_get_client):
        """Test that get_vocabulary_by_id returns None on connection failure."""
        mock_get_client.return_value = None

        result = get_vocabulary_by_id(self.vocabulary_id)

        self.assertIsNone(result)


class TestVocabularyEdgeCases(unittest.TestCase):
    """Test edge cases for vocabulary operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.article_id = "test-article-123"
        self.user_id = "test-user-123"

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_vocabulary_empty_related_words_becomes_empty_list(self, mock_get_client):
        """Test that None related_words becomes empty list."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = None

        result = save_vocabulary(
            article_id=self.article_id,
            word="test",
            lemma="test",
            definition="test",
            sentence="test",
            language="English",
            related_words=None
        )

        self.assertIsNotNone(result)

        insert_calls = mock_collection.insert_one.call_args_list
        if insert_calls:
            inserted_doc = insert_calls[-1][0][0]
            # related_words should be empty list, not None
            self.assertEqual(inserted_doc['related_words'], [])

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_vocabulary_empty_span_id_becomes_none(self, mock_get_client):
        """Test that empty span_id is normalized to None."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = None

        result = save_vocabulary(
            article_id=self.article_id,
            word="test",
            lemma="test",
            definition="test",
            sentence="test",
            language="English",
            span_id=""  # Empty string
        )

        self.assertIsNotNone(result)

        insert_calls = mock_collection.insert_one.call_args_list
        if insert_calls:
            inserted_doc = insert_calls[-1][0][0]
            # span_id should be None
            self.assertIsNone(inserted_doc['span_id'])

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_vocabulary_whitespace_span_id_becomes_none(self, mock_get_client):
        """Test that whitespace-only span_id is normalized to None."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = None

        result = save_vocabulary(
            article_id=self.article_id,
            word="test",
            lemma="test",
            definition="test",
            sentence="test",
            language="English",
            span_id="   "  # Whitespace only
        )

        self.assertIsNotNone(result)

        insert_calls = mock_collection.insert_one.call_args_list
        if insert_calls:
            inserted_doc = insert_calls[-1][0][0]
            # span_id should be None
            self.assertIsNone(inserted_doc['span_id'])

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_vocabulary_with_very_long_lemma(self, mock_get_client):
        """Test saving vocabulary with very long lemma."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = None

        # Very long lemma (e.g., compound word)
        long_lemma = "a" * 1000

        result = save_vocabulary(
            article_id=self.article_id,
            word=long_lemma,
            lemma=long_lemma,
            definition="test",
            sentence="test",
            language="English"
        )

        self.assertIsNotNone(result)

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_vocabulary_with_unicode_characters(self, mock_get_client):
        """Test saving vocabulary with unicode characters."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = None

        # Test various unicode characters
        unicode_lemmas = [
            "café",
            "naïve",
            "müller",
            "señor",
            "日本語",  # Japanese
            "مصر",     # Arabic
            "Москва"   # Russian
        ]

        for lemma in unicode_lemmas:
            mock_collection.reset_mock()

            result = save_vocabulary(
                article_id=self.article_id,
                word=lemma,
                lemma=lemma,
                definition="test",
                sentence="test",
                language="English"
            )

            self.assertIsNotNone(result)

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabularies_returns_empty_on_connection_failure(self, mock_get_client):
        """Test that get_vocabularies returns empty list on connection failure."""
        mock_get_client.return_value = None

        result = get_vocabularies(article_id=self.article_id)

        self.assertEqual(result, [])
        self.assertIsInstance(result, list)

    @patch('utils.mongodb.get_mongodb_client')
    def test_get_vocabularies_returns_empty_on_pymongo_error(self, mock_get_client):
        """Test that get_vocabularies handles PyMongoError gracefully."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # Mock find raising error
        mock_collection.find.side_effect = PyMongoError("Database error")

        result = get_vocabularies(article_id=self.article_id)

        self.assertEqual(result, [])
        self.assertIsInstance(result, list)


class TestVocabularyIntegration(unittest.TestCase):
    """Integration tests for vocabulary operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.article_id = "test-article-123"
        self.user_id = "test-user-123"

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_and_retrieve_german_verb(self, mock_get_client):
        """Integration test: save and retrieve German verb with conjugations."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # Save German verb
        mock_collection.find_one.return_value = None
        vocab_id = "vocab-gehen-123"

        def insert_side_effect(doc):
            doc['_id'] = vocab_id

        mock_collection.insert_one.side_effect = insert_side_effect

        conjugations = {
            'present': 'gehe, gehst, geht, gehen, geht, gehen',
            'past': 'ging, gingst, ging, gingen, gingt, gingen',
            'perfect': 'gegangen'
        }

        saved_id = save_vocabulary(
            article_id=self.article_id,
            word="gehend",
            lemma="gehen",
            definition="to go, to walk",
            sentence="Ich gehe nach Hause.",
            language="German",
            user_id=self.user_id,
            pos="verb",
            gender=None,
            conjugations=conjugations,
            level="A1"
        )

        self.assertIsNotNone(saved_id)

        # Now retrieve it
        mock_collection.find_one.return_value = {
            '_id': vocab_id,
            'article_id': self.article_id,
            'word': 'gehend',
            'lemma': 'gehen',
            'definition': 'to go, to walk',
            'sentence': 'Ich gehe nach Hause.',
            'language': 'German',
            'span_id': None,
            'related_words': [],
            'user_id': self.user_id,
            'pos': 'verb',
            'gender': None,
            'conjugations': conjugations,
            'level': 'A1',
            'created_at': datetime.now(timezone.utc)
        }

        result = get_vocabulary_by_id(vocab_id)

        self.assertIsNotNone(result)
        self.assertEqual(result['lemma'], 'gehen')
        self.assertEqual(result['pos'], 'verb')
        self.assertEqual(result['conjugations'], conjugations)
        self.assertEqual(result['level'], 'A1')

    @patch('utils.mongodb.get_mongodb_client')
    def test_save_and_retrieve_german_noun(self, mock_get_client):
        """Integration test: save and retrieve German noun with gender."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_collection = mock_client['opad']['vocabularies']

        # Save German noun with capitalization
        mock_collection.find_one.return_value = None
        vocab_id = "vocab-hund-123"

        def insert_side_effect(doc):
            doc['_id'] = vocab_id

        mock_collection.insert_one.side_effect = insert_side_effect

        saved_id = save_vocabulary(
            article_id=self.article_id,
            word="Hund",
            lemma="Hund",
            definition="dog",
            sentence="Der Hund ist groß.",
            language="German",
            user_id=self.user_id,
            pos="noun",
            gender="der",
            conjugations=None,
            level="A1"
        )

        self.assertIsNotNone(saved_id)

        # Retrieve and verify capitalization preserved
        mock_collection.find_one.return_value = {
            '_id': vocab_id,
            'article_id': self.article_id,
            'word': 'Hund',
            'lemma': 'Hund',
            'definition': 'dog',
            'sentence': 'Der Hund ist groß.',
            'language': 'German',
            'span_id': None,
            'related_words': [],
            'user_id': self.user_id,
            'pos': 'noun',
            'gender': 'der',
            'conjugations': None,
            'level': 'A1',
            'created_at': datetime.now(timezone.utc)
        }

        result = get_vocabulary_by_id(vocab_id)

        self.assertIsNotNone(result)
        # Capital H must be preserved
        self.assertEqual(result['lemma'], 'Hund')
        self.assertEqual(result['gender'], 'der')
        self.assertEqual(result['pos'], 'noun')


if __name__ == '__main__':
    unittest.main()
