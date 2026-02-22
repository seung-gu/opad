"""Unit tests for article_submission_service module."""

import unittest
from unittest.mock import MagicMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.article_submission_service import (
    submit_generation,
    _check_duplicate,
    _enqueue_job,
)
from adapter.fake.article_repository import FakeArticleRepository
from adapter.fake.job_queue import FakeJobQueueAdapter
from domain.model.article import (
    Article,
    ArticleInputs,
    ArticleStatus,
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
        submit_generation(
            inputs=TEST_INPUTS,
            user_id='user-123',
            repo=self.repo,
            job_queue=self.job_queue,
            force=False,
        )

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
        submit_generation(
            inputs=TEST_INPUTS,
            user_id='user-123',
            repo=self.repo,
            job_queue=self.job_queue,
            force=False,
        )

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
        article = Article.create(TEST_INPUTS, 'user-123')
        self.repo.save(article)

        self.job_queue.update_status(
            job_id=article.job_id,
            status='running',
            progress=50,
            message='Processing...',
        )

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

        status = self.job_queue.get_status(self.article.job_id)
        self.assertEqual(status['status'], 'queued')

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

        mock_repo = MagicMock()
        mock_repo.update_status.return_value = True

        with self.assertRaises(EnqueueError) as ctx:
            _enqueue_job(
                job_queue=mock_queue,
                repo=mock_repo,
                article=self.article,
            )

        self.assertIn("Failed to enqueue job", str(ctx.exception))
        mock_repo.update_status.assert_called()

    def test_enqueue_job_passes_correct_inputs(self):
        """Test that correct inputs dictionary is passed to enqueue."""
        _enqueue_job(
            job_queue=self.job_queue,
            repo=self.repo,
            article=self.article,
        )

        ctx = self.job_queue.dequeue()
        self.assertEqual(ctx.inputs.language, TEST_INPUTS.language)
        self.assertEqual(ctx.inputs.level, TEST_INPUTS.level)
        self.assertEqual(ctx.inputs.length, TEST_INPUTS.length)
        self.assertEqual(ctx.inputs.topic, TEST_INPUTS.topic)


if __name__ == '__main__':
    unittest.main()
