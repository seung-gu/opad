"""Unit tests for JobTracker context manager."""

import unittest
from unittest.mock import patch, MagicMock, Mock, call
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from worker.job_tracker import JobTracker


class TestJobTrackerInitialization(unittest.TestCase):
    """Test JobTracker initialization."""

    def test_init_stores_job_id(self):
        """Test constructor stores job_id correctly."""
        tracker = JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        self.assertEqual(tracker.job_id, "job-123")

    def test_init_stores_user_id(self):
        """Test constructor stores user_id correctly."""
        tracker = JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        self.assertEqual(tracker.user_id, "user-456")

    def test_init_stores_article_id(self):
        """Test constructor stores article_id correctly."""
        tracker = JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        self.assertEqual(tracker.article_id, "article-789")

    def test_init_with_user_id_none(self):
        """Test constructor with user_id=None."""
        tracker = JobTracker(
            job_id="job-123",
            user_id=None,
            article_id="article-789"
        )

        self.assertEqual(tracker.job_id, "job-123")
        self.assertIsNone(tracker.user_id)
        self.assertEqual(tracker.article_id, "article-789")

    def test_init_with_article_id_none(self):
        """Test constructor with article_id=None."""
        tracker = JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id=None
        )

        self.assertEqual(tracker.job_id, "job-123")
        self.assertEqual(tracker.user_id, "user-456")
        self.assertIsNone(tracker.article_id)

    def test_init_with_both_user_id_and_article_id_none(self):
        """Test constructor with both user_id and article_id as None."""
        tracker = JobTracker(
            job_id="job-123",
            user_id=None,
            article_id=None
        )

        self.assertEqual(tracker.job_id, "job-123")
        self.assertIsNone(tracker.user_id)
        self.assertIsNone(tracker.article_id)

    def test_init_listener_is_none_initially(self):
        """Test listener attribute is None initially."""
        tracker = JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        self.assertIsNone(tracker.listener)

    def test_init_token_tracker_is_none_initially(self):
        """Test token_tracker attribute is None initially."""
        tracker = JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        self.assertIsNone(tracker.token_tracker)


class TestJobTrackerEnter(unittest.TestCase):
    """Test JobTracker __enter__ method."""

    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_enter_creates_job_progress_listener(self, mock_token_tracker, mock_listener):
        """Test __enter__ creates JobProgressListener."""
        tracker = JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        result = tracker.__enter__()

        mock_listener.assert_called_once_with(
            job_id="job-123",
            article_id="article-789"
        )
        self.assertIsNotNone(tracker.listener)

    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_enter_creates_token_tracker_when_user_id_exists(self, mock_token_tracker, mock_listener):
        """Test __enter__ creates TokenTracker when user_id is not None."""
        tracker = JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        tracker.__enter__()

        mock_token_tracker.assert_called_once_with(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )
        self.assertIsNotNone(tracker.token_tracker)

    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_enter_does_not_create_token_tracker_when_user_id_is_none(self, mock_token_tracker, mock_listener):
        """Test __enter__ does NOT create TokenTracker when user_id is None."""
        tracker = JobTracker(
            job_id="job-123",
            user_id=None,
            article_id="article-789"
        )

        tracker.__enter__()

        mock_token_tracker.assert_not_called()
        self.assertIsNone(tracker.token_tracker)

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_enter_sets_litellm_callbacks_when_user_id_exists(self, mock_token_tracker_class, mock_listener, mock_litellm):
        """Test __enter__ sets litellm.callbacks when user_id exists."""
        mock_token_tracker = MagicMock()
        mock_token_tracker_class.return_value = mock_token_tracker

        tracker = JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        tracker.__enter__()

        # Verify litellm.callbacks was set to a list containing the token tracker
        self.assertEqual(mock_litellm.callbacks, [mock_token_tracker])

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_enter_does_not_set_litellm_callbacks_when_user_id_is_none(self, mock_token_tracker_class, mock_listener, mock_litellm):
        """Test __enter__ does NOT set litellm.callbacks when user_id is None."""
        tracker = JobTracker(
            job_id="job-123",
            user_id=None,
            article_id="article-789"
        )

        tracker.__enter__()

        # litellm.callbacks should not be modified
        # The mock object's attribute wasn't set, so we check the token_tracker is None
        self.assertIsNone(tracker.token_tracker)

    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_enter_returns_self(self, mock_token_tracker, mock_listener):
        """Test __enter__ returns self."""
        tracker = JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        result = tracker.__enter__()

        self.assertIs(result, tracker)

    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_enter_with_article_id_none_passes_empty_string(self, mock_token_tracker, mock_listener):
        """Test __enter__ passes empty string when article_id is None."""
        tracker = JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id=None
        )

        tracker.__enter__()

        mock_listener.assert_called_once_with(
            job_id="job-123",
            article_id=""
        )


class TestJobTrackerExit(unittest.TestCase):
    """Test JobTracker __exit__ method."""

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_exit_restores_original_litellm_callbacks(self, mock_token_tracker_class, mock_listener, mock_litellm):
        """Test __exit__ restores original litellm.callbacks when token_tracker exists."""
        mock_token_tracker = MagicMock()
        mock_token_tracker_class.return_value = mock_token_tracker

        # Set up original callbacks
        original_callbacks = [MagicMock(name="existing_callback")]
        mock_litellm.callbacks = original_callbacks.copy()

        tracker = JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        tracker.__enter__()
        tracker.__exit__(None, None, None)

        # Verify litellm.callbacks was restored to original
        self.assertEqual(mock_litellm.callbacks, original_callbacks)

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_exit_does_not_clear_litellm_when_token_tracker_is_none(self, mock_token_tracker_class, mock_listener, mock_litellm):
        """Test __exit__ does not clear litellm.callbacks when token_tracker is None."""
        tracker = JobTracker(
            job_id="job-123",
            user_id=None,
            article_id="article-789"
        )

        tracker.__enter__()
        tracker.__exit__(None, None, None)

        # litellm.callbacks should not have been modified since token_tracker was None
        mock_litellm.callbacks.__setitem__.assert_not_called()

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_exit_returns_none(self, mock_token_tracker_class, mock_listener, mock_litellm):
        """Test __exit__ returns None (does not suppress exceptions)."""
        tracker = JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        tracker.__enter__()
        result = tracker.__exit__(None, None, None)

        self.assertIsNone(result)

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_exit_with_exception_still_restores_callbacks(self, mock_token_tracker_class, mock_listener, mock_litellm):
        """Test __exit__ restores callbacks even when exception occurred."""
        mock_token_tracker = MagicMock()
        mock_token_tracker_class.return_value = mock_token_tracker

        # Set up original callbacks
        original_callbacks = [MagicMock(name="existing_callback")]
        mock_litellm.callbacks = original_callbacks.copy()

        tracker = JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        tracker.__enter__()

        # Simulate exception
        exc = ValueError("Test error")
        tracker.__exit__(ValueError, exc, None)

        # Verify litellm.callbacks was restored despite exception
        self.assertEqual(mock_litellm.callbacks, original_callbacks)

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_exit_does_not_suppress_exceptions(self, mock_token_tracker_class, mock_listener, mock_litellm):
        """Test __exit__ does not suppress exceptions (returns None)."""
        tracker = JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        tracker.__enter__()

        # __exit__ should return None (or falsy), which means exceptions propagate
        exc = RuntimeError("Test error")
        result = tracker.__exit__(RuntimeError, exc, None)

        self.assertIsNone(result)


class TestJobTrackerContextManager(unittest.TestCase):
    """Test JobTracker as context manager."""

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_with_statement_with_user_id(self, mock_token_tracker_class, mock_listener, mock_litellm):
        """Test with statement works correctly with user_id."""
        mock_token_tracker = MagicMock()
        mock_token_tracker_class.return_value = mock_token_tracker
        mock_listener_instance = MagicMock()
        mock_listener.return_value = mock_listener_instance

        # Set up original callbacks
        original_callbacks = [MagicMock(name="existing_callback")]
        mock_litellm.callbacks = original_callbacks.copy()

        with JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        ) as tracker:
            # Inside context
            self.assertIsNotNone(tracker.listener)
            self.assertIsNotNone(tracker.token_tracker)
            self.assertEqual(mock_litellm.callbacks, [mock_token_tracker])

        # After context - callbacks should be restored to original
        self.assertEqual(mock_litellm.callbacks, original_callbacks)

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_with_statement_without_user_id(self, mock_token_tracker_class, mock_listener, mock_litellm):
        """Test with statement works correctly without user_id."""
        mock_listener_instance = MagicMock()
        mock_listener.return_value = mock_listener_instance

        with JobTracker(
            job_id="job-123",
            user_id=None,
            article_id="article-789"
        ) as tracker:
            # Inside context
            self.assertIsNotNone(tracker.listener)
            self.assertIsNone(tracker.token_tracker)

        # After context - token tracker never created
        mock_token_tracker_class.assert_not_called()

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_context_manager_cleanup_on_exception(self, mock_token_tracker_class, mock_listener, mock_litellm):
        """Test cleanup happens even when exception is raised inside context."""
        mock_token_tracker = MagicMock()
        mock_token_tracker_class.return_value = mock_token_tracker
        mock_listener_instance = MagicMock()
        mock_listener.return_value = mock_listener_instance

        # Set up original callbacks
        original_callbacks = [MagicMock(name="existing_callback")]
        mock_litellm.callbacks = original_callbacks.copy()

        try:
            with JobTracker(
                job_id="job-123",
                user_id="user-456",
                article_id="article-789"
            ) as tracker:
                # Raise exception inside context
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Verify cleanup still happened - restored to original
        self.assertEqual(mock_litellm.callbacks, original_callbacks)

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_context_manager_exception_propagates(self, mock_token_tracker_class, mock_listener, mock_litellm):
        """Test that exceptions inside context propagate."""
        mock_token_tracker = MagicMock()
        mock_token_tracker_class.return_value = mock_token_tracker

        with self.assertRaises(ValueError):
            with JobTracker(
                job_id="job-123",
                user_id="user-456",
                article_id="article-789"
            ) as tracker:
                raise ValueError("Test exception")

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_multiple_trackers_independent(self, mock_token_tracker_class, mock_listener, mock_litellm):
        """Test multiple tracker instances are independent."""
        mock_token_tracker1 = MagicMock()
        mock_token_tracker2 = MagicMock()
        mock_token_tracker_class.side_effect = [mock_token_tracker1, mock_token_tracker2]

        # Set up original callbacks
        original_callbacks = [MagicMock(name="existing_callback")]
        mock_litellm.callbacks = original_callbacks.copy()

        with JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        ) as tracker1:
            # First tracker
            self.assertIs(tracker1.token_tracker, mock_token_tracker1)

        # After first tracker, restored to original
        self.assertEqual(mock_litellm.callbacks, original_callbacks)

        with JobTracker(
            job_id="job-456",
            user_id="user-789",
            article_id="article-012"
        ) as tracker2:
            # Second tracker
            self.assertIs(tracker2.token_tracker, mock_token_tracker2)

        # Both trackers had cleanup - restored to original
        self.assertEqual(mock_litellm.callbacks, original_callbacks)


class TestJobTrackerIntegration(unittest.TestCase):
    """Integration tests for JobTracker."""

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_listener_available_after_enter(self, mock_token_tracker_class, mock_listener_class, mock_litellm):
        """Test tracker.listener is available for checking task_failed status."""
        mock_listener = MagicMock()
        mock_listener.task_failed = False
        mock_listener_class.return_value = mock_listener

        with JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        ) as tracker:
            # Access listener status
            self.assertFalse(tracker.listener.task_failed)

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_full_workflow_with_user_id(self, mock_token_tracker_class, mock_listener_class, mock_litellm):
        """Test full workflow: init -> enter -> exit with user_id."""
        mock_token_tracker = MagicMock()
        mock_token_tracker_class.return_value = mock_token_tracker
        mock_listener = MagicMock()
        mock_listener.task_failed = False
        mock_listener_class.return_value = mock_listener

        # Set up original callbacks
        original_callbacks = [MagicMock(name="existing_callback")]
        mock_litellm.callbacks = original_callbacks.copy()

        # Initialize
        tracker = JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )
        self.assertIsNone(tracker.listener)
        self.assertIsNone(tracker.token_tracker)

        # Use as context manager
        with tracker as t:
            # Verify we got the same instance
            self.assertIs(t, tracker)

            # Verify components created
            self.assertIsNotNone(tracker.listener)
            self.assertIsNotNone(tracker.token_tracker)

            # Verify callbacks set
            self.assertEqual(mock_litellm.callbacks, [mock_token_tracker])

        # After exit, callbacks should be restored to original
        self.assertEqual(mock_litellm.callbacks, original_callbacks)

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_full_workflow_without_user_id(self, mock_token_tracker_class, mock_listener_class, mock_litellm):
        """Test full workflow: init -> enter -> exit without user_id."""
        mock_listener = MagicMock()
        mock_listener.task_failed = False
        mock_listener_class.return_value = mock_listener

        # Initialize
        tracker = JobTracker(
            job_id="job-123",
            user_id=None,
            article_id="article-789"
        )
        self.assertIsNone(tracker.listener)
        self.assertIsNone(tracker.token_tracker)

        # Use as context manager
        with tracker as t:
            # Verify we got the same instance
            self.assertIs(t, tracker)

            # Verify listener created
            self.assertIsNotNone(tracker.listener)

            # Verify token_tracker NOT created
            self.assertIsNone(tracker.token_tracker)

            # Verify callbacks NOT set
            mock_token_tracker_class.assert_not_called()

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_nested_context_managers(self, mock_token_tracker_class, mock_listener_class, mock_litellm):
        """Test nested JobTracker context managers restore callbacks correctly."""
        mock_token_tracker1 = MagicMock()
        mock_token_tracker2 = MagicMock()
        mock_token_tracker_class.side_effect = [mock_token_tracker1, mock_token_tracker2]

        # Set up original callbacks
        original_callbacks = [MagicMock(name="existing_callback")]
        mock_litellm.callbacks = original_callbacks.copy()

        with JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        ) as tracker1:
            self.assertEqual(mock_litellm.callbacks, [mock_token_tracker1])

            with JobTracker(
                job_id="job-456",
                user_id="user-789",
                article_id="article-012"
            ) as tracker2:
                # Inner tracker's callbacks set
                self.assertEqual(mock_litellm.callbacks, [mock_token_tracker2])

            # After inner exit, outer context's callbacks should be restored
            # Inner tracker saved [mock_token_tracker1] as its original, so restores to that
            self.assertEqual(mock_litellm.callbacks, [mock_token_tracker1])

        # After outer exit, restored to original callbacks
        self.assertEqual(mock_litellm.callbacks, original_callbacks)


class TestJobTrackerEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_with_empty_string_job_id(self, mock_token_tracker_class, mock_listener_class, mock_litellm):
        """Test with empty string job_id."""
        tracker = JobTracker(
            job_id="",
            user_id="user-456",
            article_id="article-789"
        )

        self.assertEqual(tracker.job_id, "")

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_with_empty_string_user_id(self, mock_token_tracker_class, mock_listener_class, mock_litellm):
        """Test with empty string user_id (falsy but not None)."""
        tracker = JobTracker(
            job_id="job-123",
            user_id="",
            article_id="article-789"
        )

        # Empty string is falsy, so token_tracker should not be created
        tracker.__enter__()

        mock_token_tracker_class.assert_not_called()
        self.assertIsNone(tracker.token_tracker)

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_with_empty_string_article_id(self, mock_token_tracker_class, mock_listener_class, mock_litellm):
        """Test with empty string article_id."""
        tracker = JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id=""
        )

        tracker.__enter__()

        # Empty string article_id should still be passed
        mock_listener_class.assert_called_once_with(
            job_id="job-123",
            article_id=""
        )

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_with_very_long_strings(self, mock_token_tracker_class, mock_listener_class, mock_litellm):
        """Test with very long ID strings."""
        long_id = "x" * 1000

        tracker = JobTracker(
            job_id=long_id,
            user_id=long_id,
            article_id=long_id
        )

        self.assertEqual(tracker.job_id, long_id)
        self.assertEqual(tracker.user_id, long_id)
        self.assertEqual(tracker.article_id, long_id)

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_exit_called_without_enter(self, mock_token_tracker_class, mock_listener_class, mock_litellm):
        """Test __exit__ called without __enter__ (token_tracker is None)."""
        tracker = JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        # Call __exit__ without __enter__
        result = tracker.__exit__(None, None, None)

        # Should not crash and return None
        self.assertIsNone(result)

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_multiple_exits(self, mock_token_tracker_class, mock_listener_class, mock_litellm):
        """Test calling __exit__ multiple times."""
        mock_token_tracker = MagicMock()
        mock_token_tracker_class.return_value = mock_token_tracker

        # Set up original callbacks
        original_callbacks = [MagicMock(name="existing_callback")]
        mock_litellm.callbacks = original_callbacks.copy()

        tracker = JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        tracker.__enter__()

        # Call __exit__ multiple times
        tracker.__exit__(None, None, None)
        tracker.__exit__(None, None, None)

        # Should not crash and restore to original
        self.assertEqual(mock_litellm.callbacks, original_callbacks)

    @patch('worker.job_tracker.litellm')
    @patch('worker.job_tracker.JobProgressListener')
    @patch('worker.job_tracker.ArticleGenerationTokenTracker')
    def test_enter_called_multiple_times(self, mock_token_tracker_class, mock_listener_class, mock_litellm):
        """Test calling __enter__ multiple times overwrites previous instance."""
        mock_token_tracker1 = MagicMock()
        mock_token_tracker2 = MagicMock()
        mock_token_tracker_class.side_effect = [mock_token_tracker1, mock_token_tracker2]

        tracker = JobTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        tracker.__enter__()
        first_token_tracker = tracker.token_tracker

        tracker.__enter__()
        second_token_tracker = tracker.token_tracker

        # Second enter should have created a new token tracker
        self.assertIsNotNone(first_token_tracker)
        self.assertIsNotNone(second_token_tracker)


if __name__ == '__main__':
    unittest.main()
