"""Unit tests for article_generation_service module."""

import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.article_generation_service import (
    generate_article,
    _get_vocabulary,
)
from adapter.fake.article_repository import FakeArticleRepository
from domain.model.article import (
    Article,
    ArticleInputs,
    ArticleStatus,
    SourceInfo,
    EditRecord,
    GenerationResult,
)


TEST_INPUTS = ArticleInputs(language='German', level='B2', length='500', topic='AI')


class TestGetVocabulary(unittest.TestCase):
    """Test _get_vocabulary function."""

    def test_get_vocabulary_returns_empty_if_no_user_id(self):
        """Test that empty list is returned when user_id is None."""
        result = _get_vocabulary(
            user_id=None,
            language='German',
            level='B2',
            vocab=MagicMock(),
        )

        self.assertEqual(result, [])

    def test_get_vocabulary_returns_empty_if_no_language(self):
        """Test that empty list is returned when language is empty."""
        result = _get_vocabulary(
            user_id='user-123',
            language='',
            level='B2',
            vocab=MagicMock(),
        )

        self.assertEqual(result, [])

    def test_get_vocabulary_returns_empty_if_no_vocab_port(self):
        """Test that empty list is returned when vocab port is None."""
        result = _get_vocabulary(
            user_id='user-123',
            language='German',
            level='B2',
            vocab=None,
        )

        self.assertEqual(result, [])

    def test_get_vocabulary_filters_by_cefr_range(self):
        """Test that vocabulary is filtered by correct CEFR range."""
        mock_vocab = MagicMock()
        mock_vocab.find_lemmas.return_value = ['word1', 'word2']

        result = _get_vocabulary(
            user_id='user-123',
            language='German',
            level='B2',
            vocab=mock_vocab,
        )

        # Verify find_lemmas was called with correct parameters
        mock_vocab.find_lemmas.assert_called_once()
        call_kwargs = mock_vocab.find_lemmas.call_args[1]

        self.assertEqual(call_kwargs['user_id'], 'user-123')
        self.assertEqual(call_kwargs['language'], 'German')
        # B2 should include A1, A2, B1, B2, and optionally B2+1 (C1)
        self.assertIn('B2', call_kwargs['levels'])
        self.assertEqual(call_kwargs['limit'], 50)

    def test_get_vocabulary_returns_vocab_list(self):
        """Test that vocabulary list is returned correctly."""
        expected_lemmas = ['laufen', 'gehen', 'sprechen']
        mock_vocab = MagicMock()
        mock_vocab.find_lemmas.return_value = expected_lemmas

        result = _get_vocabulary(
            user_id='user-123',
            language='German',
            level='B2',
            vocab=mock_vocab,
        )

        self.assertEqual(result, expected_lemmas)

    def test_get_vocabulary_returns_empty_if_none_returned(self):
        """Test that empty list is returned if find_lemmas returns None."""
        mock_vocab = MagicMock()
        mock_vocab.find_lemmas.return_value = None

        result = _get_vocabulary(
            user_id='user-123',
            language='German',
            level='B2',
            vocab=mock_vocab,
        )

        self.assertEqual(result, [])


class TestGenerateArticle(unittest.TestCase):
    """Test generate_article function."""

    def setUp(self):
        """Set up test fixtures."""
        self.repo = FakeArticleRepository()
        self.article = Article.create(TEST_INPUTS, 'user-123')
        self.repo.save(self.article)

    def test_generate_article_success(self):
        """Test successful article generation."""
        mock_generator = MagicMock()
        result = GenerationResult(
            content='Test article content',
            source=SourceInfo(
                title='Test Title',
                source_name='Test Source',
                source_url='https://example.com',
            ),
            edit_history=[],
            agent_usage=[],
        )
        mock_generator.generate.return_value = result

        success = generate_article(
            article=self.article,
            user_id='user-123',
            inputs=TEST_INPUTS,
            generator=mock_generator,
            repo=self.repo,
            token_usage_repo=None,
            vocab=None,
            llm=None,
            job_id='job-123',
        )

        self.assertTrue(success)

    def test_generate_article_updates_article_status(self):
        """Test that article status is updated to COMPLETED."""
        mock_generator = MagicMock()
        result = GenerationResult(
            content='Test article content',
            source=SourceInfo(
                title='Test Title',
                source_name='Test Source',
            ),
            edit_history=[],
            agent_usage=[],
        )
        mock_generator.generate.return_value = result

        generate_article(
            article=self.article,
            user_id='user-123',
            inputs=TEST_INPUTS,
            generator=mock_generator,
            repo=self.repo,
        )

        saved_article = self.repo.get_by_id(self.article.id)
        self.assertEqual(saved_article.status, ArticleStatus.COMPLETED)
        self.assertEqual(saved_article.content, 'Test article content')

    def test_generate_article_saves_source_and_edit_history(self):
        """Test that source and edit_history are saved."""
        mock_generator = MagicMock()
        edit_records = [
            EditRecord(
                original='Old sentence',
                replaced='New sentence',
                rationale='Clarity',
            ),
        ]
        result = GenerationResult(
            content='Test article content',
            source=SourceInfo(
                title='Test Title',
                source_name='Test Source',
                source_url='https://example.com',
                author='John Doe',
            ),
            edit_history=edit_records,
            agent_usage=[],
        )
        mock_generator.generate.return_value = result

        generate_article(
            article=self.article,
            user_id='user-123',
            inputs=TEST_INPUTS,
            generator=mock_generator,
            repo=self.repo,
        )

        saved_article = self.repo.get_by_id(self.article.id)
        self.assertIsNotNone(saved_article.source)
        self.assertEqual(saved_article.source.title, 'Test Title')
        self.assertEqual(saved_article.source.author, 'John Doe')
        self.assertEqual(len(saved_article.edit_history), 1)
        self.assertEqual(saved_article.edit_history[0].original, 'Old sentence')

    def test_generate_article_returns_false_if_save_fails(self):
        """Test that False is returned if repo.save fails."""
        mock_generator = MagicMock()
        result = GenerationResult(
            content='Test article content',
            source=SourceInfo(
                title='Test Title',
                source_name='Test Source',
            ),
            edit_history=[],
            agent_usage=[],
        )
        mock_generator.generate.return_value = result

        mock_repo = MagicMock()
        mock_repo.save.return_value = False

        success = generate_article(
            article=self.article,
            user_id='user-123',
            inputs=TEST_INPUTS,
            generator=mock_generator,
            repo=mock_repo,
        )

        self.assertFalse(success)

    def test_generate_article_passes_job_context_to_generator(self):
        """Test that job_id and article_id are passed to generate()."""
        mock_generator = MagicMock()
        result = GenerationResult(
            content='Test article content',
            source=SourceInfo(
                title='Test Title',
                source_name='Test Source',
            ),
            edit_history=[],
            agent_usage=[],
        )
        mock_generator.generate.return_value = result

        generate_article(
            article=self.article,
            user_id='user-123',
            inputs=TEST_INPUTS,
            generator=mock_generator,
            repo=self.repo,
            job_id='job-123',
        )

        mock_generator.generate.assert_called_once()
        call_kwargs = mock_generator.generate.call_args[1]
        self.assertEqual(call_kwargs['job_id'], 'job-123')
        self.assertEqual(call_kwargs['article_id'], self.article.id)

    def test_generate_article_uses_empty_job_id_when_none(self):
        """Test that empty string is passed when job_id is None."""
        mock_generator = MagicMock()
        result = GenerationResult(
            content='Test article content',
            source=SourceInfo(
                title='Test Title',
                source_name='Test Source',
            ),
            edit_history=[],
            agent_usage=[],
        )
        mock_generator.generate.return_value = result

        generate_article(
            article=self.article,
            user_id='user-123',
            inputs=TEST_INPUTS,
            generator=mock_generator,
            repo=self.repo,
            job_id=None,
        )

        call_kwargs = mock_generator.generate.call_args[1]
        self.assertEqual(call_kwargs['job_id'], '')

    @patch('services.article_generation_service.track_agent_usage')
    def test_generate_article_tracks_token_usage(self, mock_track):
        """Test that token usage is tracked when available."""
        mock_generator = MagicMock()
        agent_usage = [
            {
                'agent_role': 'researcher',
                'agent_name': 'ArticleResearcher',
                'model': 'gpt-4',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150,
            },
        ]
        result = GenerationResult(
            content='Test article content',
            source=SourceInfo(
                title='Test Title',
                source_name='Test Source',
            ),
            edit_history=[],
            agent_usage=agent_usage,
        )
        mock_generator.generate.return_value = result

        mock_token_repo = MagicMock()
        mock_llm = MagicMock()

        generate_article(
            article=self.article,
            user_id='user-123',
            inputs=TEST_INPUTS,
            generator=mock_generator,
            repo=self.repo,
            token_usage_repo=mock_token_repo,
            llm=mock_llm,
            job_id='job-123',
        )

        # Verify track_agent_usage was called
        mock_track.assert_called_once()
        call_args = mock_track.call_args[0]
        self.assertEqual(call_args[0], mock_token_repo)  # token_usage_repo
        self.assertEqual(call_args[2], 'user-123')       # user_id
        self.assertEqual(call_args[3], self.article.id)   # article_id
        self.assertEqual(call_args[4], 'job-123')         # job_id

    def test_generate_article_skips_token_tracking_if_no_user_id(self):
        """Test that token tracking is skipped if user_id is None."""
        mock_generator = MagicMock()
        agent_usage = [
            {
                'agent_role': 'researcher',
                'model': 'gpt-4',
                'total_tokens': 150,
            },
        ]
        result = GenerationResult(
            content='Test article content',
            source=SourceInfo(
                title='Test Title',
                source_name='Test Source',
            ),
            edit_history=[],
            agent_usage=agent_usage,
        )
        mock_generator.generate.return_value = result

        mock_token_repo = MagicMock()

        with patch('services.article_generation_service.track_agent_usage') as mock_track:
            success = generate_article(
                article=self.article,
                user_id=None,  # No user
                inputs=TEST_INPUTS,
                generator=mock_generator,
                repo=self.repo,
                token_usage_repo=mock_token_repo,
            )

            self.assertTrue(success)
            mock_track.assert_not_called()

    def test_generate_article_skips_token_tracking_if_no_usage_data(self):
        """Test that token tracking is skipped if agent_usage is None."""
        mock_generator = MagicMock()
        result = GenerationResult(
            content='Test article content',
            source=SourceInfo(
                title='Test Title',
                source_name='Test Source',
            ),
            edit_history=[],
            agent_usage=None,  # No usage data
        )
        mock_generator.generate.return_value = result

        mock_token_repo = MagicMock()

        with patch('services.article_generation_service.track_agent_usage') as mock_track:
            success = generate_article(
                article=self.article,
                user_id='user-123',
                inputs=TEST_INPUTS,
                generator=mock_generator,
                repo=self.repo,
                token_usage_repo=mock_token_repo,
            )

            self.assertTrue(success)
            mock_track.assert_not_called()

    def test_generate_article_gets_vocabulary(self):
        """Test that vocabulary is retrieved and passed to generator."""
        mock_generator = MagicMock()
        result = GenerationResult(
            content='Test article content',
            source=SourceInfo(
                title='Test Title',
                source_name='Test Source',
            ),
            edit_history=[],
            agent_usage=[],
        )
        mock_generator.generate.return_value = result

        mock_vocab = MagicMock()
        mock_vocab.find_lemmas.return_value = ['word1', 'word2']

        generate_article(
            article=self.article,
            user_id='user-123',
            inputs=TEST_INPUTS,
            generator=mock_generator,
            repo=self.repo,
            vocab=mock_vocab,
        )

        # Verify generator.generate was called with vocabulary
        mock_generator.generate.assert_called_once()
        call_args = mock_generator.generate.call_args
        vocab_arg = call_args[0][1]  # Second positional argument
        self.assertEqual(vocab_arg, ['word1', 'word2'])


if __name__ == '__main__':
    unittest.main()
