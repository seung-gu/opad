"""Unit tests for article_generation_service module."""

import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.article_generation_service import (
    submit_generation,
    generate_article,
    _check_duplicate,
    _enqueue_job,
    _get_vocabulary,
)
from adapter.fake.article_repository import FakeArticleRepository
from adapter.fake.job_queue import FakeJobQueueAdapter
from domain.model.article import (
    Article,
    ArticleInputs,
    ArticleStatus,
    SourceInfo,
    EditRecord,
    GenerationResult,
)
from domain.model.errors import (
    DuplicateArticleError,
    EnqueueError,
    DomainError,
)


TEST_INPUTS = ArticleInputs(language='German', level='B2', length='500', topic='AI')


class TestSubmitGeneration(unittest.TestCase):
    """Test submit_generation function."""

    def setUp(self):
        """Set up test fixtures."""
        self.repo = FakeArticleRepository()
        self.job_queue = FakeJobQueueAdapter()

    def test_submit_generation_success(self):
        """Test successful article submission."""
        article = submit_generation(
            inputs=TEST_INPUTS,
            user_id='user-123',
            repo=self.repo,
            job_queue=self.job_queue,
            force=False,
        )

        self.assertIsNotNone(article)
        self.assertEqual(article.user_id, 'user-123')
        self.assertEqual(article.inputs, TEST_INPUTS)
        self.assertEqual(article.status, ArticleStatus.RUNNING)
        self.assertIsNotNone(article.job_id)
        self.assertIsNotNone(article.id)

    def test_submit_generation_creates_article_in_repo(self):
        """Test that submitted article is saved to repository."""
        article = submit_generation(
            inputs=TEST_INPUTS,
            user_id='user-123',
            repo=self.repo,
            job_queue=self.job_queue,
            force=False,
        )

        saved_article = self.repo.get_by_id(article.id)
        self.assertIsNotNone(saved_article)
        self.assertEqual(saved_article.id, article.id)

    def test_submit_generation_enqueues_job(self):
        """Test that job is enqueued in job queue."""
        article = submit_generation(
            inputs=TEST_INPUTS,
            user_id='user-123',
            repo=self.repo,
            job_queue=self.job_queue,
            force=False,
        )

        status = self.job_queue.get_status(article.job_id)
        self.assertIsNotNone(status)
        self.assertEqual(status['status'], 'queued')
        self.assertEqual(status['article_id'], article.id)

    def test_submit_generation_raises_duplicate_error(self):
        """Test that duplicate article raises DuplicateArticleError."""
        # Create first article
        first = submit_generation(
            inputs=TEST_INPUTS,
            user_id='user-123',
            repo=self.repo,
            job_queue=self.job_queue,
            force=False,
        )

        # Try to submit identical inputs again
        with self.assertRaises(DuplicateArticleError):
            submit_generation(
                inputs=TEST_INPUTS,
                user_id='user-123',
                repo=self.repo,
                job_queue=self.job_queue,
                force=False,
            )

    def test_submit_generation_force_skips_duplicate_check(self):
        """Test that force=True bypasses duplicate checking."""
        # Create first article
        submit_generation(
            inputs=TEST_INPUTS,
            user_id='user-123',
            repo=self.repo,
            job_queue=self.job_queue,
            force=False,
        )

        # Submit identical inputs with force=True (should succeed)
        article = submit_generation(
            inputs=TEST_INPUTS,
            user_id='user-123',
            repo=self.repo,
            job_queue=self.job_queue,
            force=True,
        )

        self.assertIsNotNone(article)

    def test_submit_generation_fails_if_repo_save_fails(self):
        """Test that DomainError is raised if repo.save fails."""
        mock_repo = MagicMock()
        mock_repo.save.return_value = False
        mock_repo.find_duplicate.return_value = None
        mock_job_queue = MagicMock()

        with self.assertRaises(DomainError) as ctx:
            submit_generation(
                inputs=TEST_INPUTS,
                user_id='user-123',
                repo=mock_repo,
                job_queue=mock_job_queue,
                force=False,
            )

        self.assertIn("Failed to save article", str(ctx.exception))

    def test_submit_generation_raises_enqueue_error_if_queue_fails(self):
        """Test that EnqueueError is raised if job_queue fails."""
        mock_repo = MagicMock()
        mock_repo.save.return_value = True
        mock_repo.find_duplicate.return_value = None
        mock_repo.update_status.return_value = True

        mock_job_queue = MagicMock()
        # First update_status call succeeds, second (enqueue status) succeeds, but enqueue fails
        mock_job_queue.update_status.return_value = True
        mock_job_queue.enqueue.return_value = False

        with self.assertRaises(EnqueueError) as ctx:
            submit_generation(
                inputs=TEST_INPUTS,
                user_id='user-123',
                repo=mock_repo,
                job_queue=mock_job_queue,
                force=False,
            )

        self.assertIn("Failed to enqueue job", str(ctx.exception))


class TestCheckDuplicate(unittest.TestCase):
    """Test _check_duplicate function."""

    def setUp(self):
        """Set up test fixtures."""
        self.repo = FakeArticleRepository()
        self.job_queue = FakeJobQueueAdapter()

    def test_check_duplicate_returns_if_force_is_true(self):
        """Test that no error is raised when force=True."""
        # This should not raise any exception
        _check_duplicate(
            repo=self.repo,
            job_queue=self.job_queue,
            inputs=TEST_INPUTS,
            force=True,
            user_id='user-123',
        )

    def test_check_duplicate_returns_if_no_duplicate_exists(self):
        """Test that no error is raised when no duplicate exists."""
        _check_duplicate(
            repo=self.repo,
            job_queue=self.job_queue,
            inputs=TEST_INPUTS,
            force=False,
            user_id='user-123',
        )

    def test_check_duplicate_raises_with_job_status(self):
        """Test that DuplicateArticleError includes job status when available."""
        # Create an article first
        article = Article.create(TEST_INPUTS, 'user-123')
        self.repo.save(article)

        # Set job status in queue
        self.job_queue.update_status(
            job_id=article.job_id,
            status='running',
            progress=50,
            message='Processing...',
        )

        # Now check duplicate should raise with job data
        with self.assertRaises(DuplicateArticleError) as ctx:
            _check_duplicate(
                repo=self.repo,
                job_queue=self.job_queue,
                inputs=TEST_INPUTS,
                force=False,
                user_id='user-123',
            )

        error = ctx.exception
        self.assertEqual(error.article_id, article.id)
        self.assertIsNotNone(error.job_data)
        self.assertEqual(error.job_data['status'], 'running')

    def test_check_duplicate_raises_without_job_status(self):
        """Test that DuplicateArticleError works when job_id is None."""
        # Create article without job_id
        article = Article.create(TEST_INPUTS, 'user-123')
        article.job_id = None
        self.repo.save(article)

        with self.assertRaises(DuplicateArticleError) as ctx:
            _check_duplicate(
                repo=self.repo,
                job_queue=self.job_queue,
                inputs=TEST_INPUTS,
                force=False,
                user_id='user-123',
            )

        error = ctx.exception
        self.assertEqual(error.article_id, article.id)
        self.assertIsNone(error.job_data)


class TestEnqueueJob(unittest.TestCase):
    """Test _enqueue_job function."""

    def setUp(self):
        """Set up test fixtures."""
        self.repo = FakeArticleRepository()
        self.job_queue = FakeJobQueueAdapter()
        self.article = Article.create(TEST_INPUTS, 'user-123')

    def test_enqueue_job_success(self):
        """Test successful job enqueueing."""
        _enqueue_job(
            job_queue=self.job_queue,
            repo=self.repo,
            article=self.article,
        )

        # Verify status was updated
        status = self.job_queue.get_status(self.article.job_id)
        self.assertEqual(status['status'], 'queued')

        # Verify job is in queue
        ctx = self.job_queue.dequeue()
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.job_id, self.article.job_id)
        self.assertEqual(ctx.article_id, self.article.id)

    def test_enqueue_job_raises_if_update_status_fails(self):
        """Test EnqueueError when update_status fails."""
        mock_queue = MagicMock()
        mock_queue.update_status.return_value = False

        with self.assertRaises(EnqueueError) as ctx:
            _enqueue_job(
                job_queue=mock_queue,
                repo=self.repo,
                article=self.article,
            )

        self.assertIn("Failed to initialize job status", str(ctx.exception))

    def test_enqueue_job_raises_if_enqueue_fails(self):
        """Test EnqueueError when enqueue fails."""
        mock_queue = MagicMock()
        mock_queue.update_status.return_value = True
        mock_queue.enqueue.return_value = False

        # Mock repo to verify update_status is called on failure
        mock_repo = MagicMock()
        mock_repo.update_status.return_value = True

        with self.assertRaises(EnqueueError) as ctx:
            _enqueue_job(
                job_queue=mock_queue,
                repo=mock_repo,
                article=self.article,
            )

        self.assertIn("Failed to enqueue job", str(ctx.exception))
        # Verify article status was updated to FAILED
        mock_repo.update_status.assert_called()

    def test_enqueue_job_passes_correct_inputs(self):
        """Test that correct inputs dictionary is passed to enqueue."""
        _enqueue_job(
            job_queue=self.job_queue,
            repo=self.repo,
            article=self.article,
        )

        # Dequeue and check inputs
        ctx = self.job_queue.dequeue()
        self.assertEqual(ctx.inputs.language, TEST_INPUTS.language)
        self.assertEqual(ctx.inputs.level, TEST_INPUTS.level)
        self.assertEqual(ctx.inputs.length, TEST_INPUTS.length)
        self.assertEqual(ctx.inputs.topic, TEST_INPUTS.topic)


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
