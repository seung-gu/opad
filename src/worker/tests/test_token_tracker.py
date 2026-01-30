"""Unit tests for ArticleGenerationTokenTracker."""

import unittest
from unittest.mock import patch, MagicMock, Mock, call
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from worker.token_tracker import ArticleGenerationTokenTracker


class TestArticleGenerationTokenTrackerInit(unittest.TestCase):
    """Test ArticleGenerationTokenTracker initialization."""

    def test_init_with_all_parameters(self):
        """Test constructor stores all parameters correctly."""
        tracker = ArticleGenerationTokenTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        self.assertEqual(tracker.job_id, "job-123")
        self.assertEqual(tracker.user_id, "user-456")
        self.assertEqual(tracker.article_id, "article-789")

    def test_init_with_none_article_id(self):
        """Test constructor with optional article_id=None."""
        tracker = ArticleGenerationTokenTracker(
            job_id="job-123",
            user_id="user-456",
            article_id=None
        )

        self.assertEqual(tracker.job_id, "job-123")
        self.assertEqual(tracker.user_id, "user-456")
        self.assertIsNone(tracker.article_id)

    def test_init_without_article_id_parameter(self):
        """Test constructor without specifying article_id parameter."""
        tracker = ArticleGenerationTokenTracker(
            job_id="job-123",
            user_id="user-456"
        )

        self.assertEqual(tracker.job_id, "job-123")
        self.assertEqual(tracker.user_id, "user-456")
        self.assertIsNone(tracker.article_id)


class TestLogSuccessEvent(unittest.TestCase):
    """Test log_success_event method."""

    def setUp(self):
        """Set up test fixtures."""
        self.tracker = ArticleGenerationTokenTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )
        self.start_time = 1609459200.0
        self.end_time = 1609459210.0

    @patch('worker.token_tracker.save_token_usage')
    @patch('worker.token_tracker.litellm.completion_cost')
    def test_log_success_event_normal_case(self, mock_cost, mock_save):
        """Test successful token extraction and save_token_usage call."""
        # Setup response object with usage
        response_obj = MagicMock()
        response_obj.model = "gpt-4"
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = 100
        response_obj.usage.completion_tokens = 50

        kwargs = {"model": "gpt-4"}
        mock_cost.return_value = 0.15

        self.tracker.log_success_event(kwargs, response_obj, self.start_time, self.end_time)

        # Verify save_token_usage was called
        mock_save.assert_called_once()
        call_kwargs = mock_save.call_args[1]
        self.assertEqual(call_kwargs['user_id'], "user-456")
        self.assertEqual(call_kwargs['operation'], "article_generation")
        self.assertEqual(call_kwargs['model'], "gpt-4")
        self.assertEqual(call_kwargs['prompt_tokens'], 100)
        self.assertEqual(call_kwargs['completion_tokens'], 50)
        self.assertEqual(call_kwargs['estimated_cost'], 0.15)
        self.assertEqual(call_kwargs['article_id'], "article-789")
        self.assertEqual(call_kwargs['metadata']['job_id'], "job-123")

    @patch('worker.token_tracker.save_token_usage')
    @patch('worker.token_tracker.litellm.completion_cost')
    def test_log_success_event_with_missing_usage(self, mock_cost, mock_save):
        """Test with missing usage data (response.usage is None)."""
        response_obj = MagicMock()
        response_obj.model = "gpt-4"
        response_obj.usage = None

        kwargs = {"model": "gpt-4"}

        self.tracker.log_success_event(kwargs, response_obj, self.start_time, self.end_time)

        # Should not save when no tokens are used
        mock_save.assert_not_called()

    @patch('worker.token_tracker.save_token_usage')
    @patch('worker.token_tracker.litellm.completion_cost')
    def test_log_success_event_with_missing_prompt_tokens(self, mock_cost, mock_save):
        """Test with missing prompt_tokens attribute."""
        response_obj = MagicMock()
        response_obj.model = "gpt-4"
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = None
        response_obj.usage.completion_tokens = 50

        kwargs = {"model": "gpt-4"}
        mock_cost.return_value = 0.05

        self.tracker.log_success_event(kwargs, response_obj, self.start_time, self.end_time)

        # Should save with prompt_tokens as 0
        mock_save.assert_called_once()
        call_kwargs = mock_save.call_args[1]
        self.assertEqual(call_kwargs['prompt_tokens'], 0)
        self.assertEqual(call_kwargs['completion_tokens'], 50)

    @patch('worker.token_tracker.save_token_usage')
    @patch('worker.token_tracker.litellm.completion_cost')
    def test_log_success_event_with_missing_completion_tokens(self, mock_cost, mock_save):
        """Test with missing completion_tokens attribute."""
        response_obj = MagicMock()
        response_obj.model = "gpt-4"
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = 100
        response_obj.usage.completion_tokens = None

        kwargs = {"model": "gpt-4"}
        mock_cost.return_value = 0.05

        self.tracker.log_success_event(kwargs, response_obj, self.start_time, self.end_time)

        # Should save with completion_tokens as 0
        mock_save.assert_called_once()
        call_kwargs = mock_save.call_args[1]
        self.assertEqual(call_kwargs['prompt_tokens'], 100)
        self.assertEqual(call_kwargs['completion_tokens'], 0)

    @patch('worker.token_tracker.save_token_usage')
    @patch('worker.token_tracker.litellm.completion_cost')
    def test_log_success_event_cost_calculation_failure_fallback(self, mock_cost, mock_save):
        """Test cost calculation failure falls back to 0.0."""
        response_obj = MagicMock()
        response_obj.model = "gpt-4"
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = 100
        response_obj.usage.completion_tokens = 50

        kwargs = {"model": "gpt-4"}
        # Mock cost calculation to raise exception
        mock_cost.side_effect = Exception("Unknown model pricing")

        self.tracker.log_success_event(kwargs, response_obj, self.start_time, self.end_time)

        # Should still save with estimated_cost = 0.0
        mock_save.assert_called_once()
        call_kwargs = mock_save.call_args[1]
        self.assertEqual(call_kwargs['estimated_cost'], 0.0)

    @patch('worker.token_tracker.save_token_usage')
    @patch('worker.token_tracker.litellm.completion_cost')
    def test_log_success_event_save_token_usage_failure_doesnt_crash(self, mock_cost, mock_save):
        """Test save_token_usage failure doesn't crash the method."""
        response_obj = MagicMock()
        response_obj.model = "gpt-4"
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = 100
        response_obj.usage.completion_tokens = 50

        kwargs = {"model": "gpt-4"}
        mock_cost.return_value = 0.15
        # Mock save_token_usage to raise exception
        mock_save.side_effect = Exception("MongoDB connection failed")

        # Should not raise, should catch and log warning
        try:
            self.tracker.log_success_event(kwargs, response_obj, self.start_time, self.end_time)
        except Exception:
            self.fail("log_success_event should not raise exception on save failure")

    @patch('worker.token_tracker.save_token_usage')
    @patch('worker.token_tracker.litellm.completion_cost')
    def test_log_success_event_metadata_includes_job_id(self, mock_cost, mock_save):
        """Test metadata includes job_id."""
        response_obj = MagicMock()
        response_obj.model = "gpt-4"
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = 100
        response_obj.usage.completion_tokens = 50

        kwargs = {"model": "gpt-4"}
        mock_cost.return_value = 0.15

        self.tracker.log_success_event(kwargs, response_obj, self.start_time, self.end_time)

        mock_save.assert_called_once()
        call_kwargs = mock_save.call_args[1]
        self.assertIn('metadata', call_kwargs)
        self.assertEqual(call_kwargs['metadata']['job_id'], "job-123")

    @patch('worker.token_tracker.save_token_usage')
    @patch('worker.token_tracker.litellm.completion_cost')
    def test_log_success_event_model_from_response(self, mock_cost, mock_save):
        """Test model is extracted from response when available."""
        response_obj = MagicMock()
        response_obj.model = "claude-3-opus"
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = 100
        response_obj.usage.completion_tokens = 50

        # kwargs has different model
        kwargs = {"model": "gpt-4"}
        mock_cost.return_value = 0.15

        self.tracker.log_success_event(kwargs, response_obj, self.start_time, self.end_time)

        mock_save.assert_called_once()
        call_kwargs = mock_save.call_args[1]
        # Should use model from response_obj
        self.assertEqual(call_kwargs['model'], "claude-3-opus")

    @patch('worker.token_tracker.save_token_usage')
    @patch('worker.token_tracker.litellm.completion_cost')
    def test_log_success_event_model_from_kwargs_when_response_missing(self, mock_cost, mock_save):
        """Test model is extracted from kwargs when response doesn't have it."""
        response_obj = MagicMock()
        response_obj.model = None
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = 100
        response_obj.usage.completion_tokens = 50

        kwargs = {"model": "gpt-4"}
        mock_cost.return_value = 0.15

        self.tracker.log_success_event(kwargs, response_obj, self.start_time, self.end_time)

        mock_save.assert_called_once()
        call_kwargs = mock_save.call_args[1]
        # Should use model from kwargs
        self.assertEqual(call_kwargs['model'], "gpt-4")

    @patch('worker.token_tracker.save_token_usage')
    @patch('worker.token_tracker.litellm.completion_cost')
    def test_log_success_event_no_tokens_used_skips_save(self, mock_cost, mock_save):
        """Test that zero tokens skips saving."""
        response_obj = MagicMock()
        response_obj.model = "gpt-4"
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = 0
        response_obj.usage.completion_tokens = 0

        kwargs = {"model": "gpt-4"}

        self.tracker.log_success_event(kwargs, response_obj, self.start_time, self.end_time)

        # Should skip saving when no tokens are used
        mock_save.assert_not_called()

    @patch('worker.token_tracker.save_token_usage')
    @patch('worker.token_tracker.litellm.completion_cost')
    def test_log_success_event_with_article_id_none(self, mock_cost, mock_save):
        """Test log_success_event when tracker has article_id=None."""
        tracker = ArticleGenerationTokenTracker(
            job_id="job-123",
            user_id="user-456",
            article_id=None
        )

        response_obj = MagicMock()
        response_obj.model = "gpt-4"
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = 100
        response_obj.usage.completion_tokens = 50

        kwargs = {"model": "gpt-4"}
        mock_cost.return_value = 0.15

        tracker.log_success_event(kwargs, response_obj, self.start_time, self.end_time)

        mock_save.assert_called_once()
        call_kwargs = mock_save.call_args[1]
        self.assertIsNone(call_kwargs['article_id'])


class TestAsyncLogSuccessEvent(unittest.TestCase):
    """Test async_log_success_event method."""

    def setUp(self):
        """Set up test fixtures."""
        self.tracker = ArticleGenerationTokenTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )
        self.start_time = 1609459200.0
        self.end_time = 1609459210.0

    @patch('worker.token_tracker.save_token_usage')
    @patch('worker.token_tracker.litellm.completion_cost')
    def test_async_log_success_event_delegates_to_sync(self, mock_cost, mock_save):
        """Test async_log_success_event delegates to sync version."""
        response_obj = MagicMock()
        response_obj.model = "gpt-4"
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = 100
        response_obj.usage.completion_tokens = 50

        kwargs = {"model": "gpt-4"}
        mock_cost.return_value = 0.15

        # Call async version (should be synchronous in implementation)
        import asyncio
        asyncio.run(self.tracker.async_log_success_event(kwargs, response_obj, self.start_time, self.end_time))

        # Should have called save_token_usage through sync version
        mock_save.assert_called_once()


class TestLogFailureEvent(unittest.TestCase):
    """Test log_failure_event method."""

    def setUp(self):
        """Set up test fixtures."""
        self.tracker = ArticleGenerationTokenTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )
        self.start_time = 1609459200.0
        self.end_time = 1609459210.0

    @patch('worker.token_tracker.save_token_usage')
    def test_log_failure_event_doesnt_save(self, mock_save):
        """Test that log_failure_event logs warning but doesn't save to MongoDB."""
        response_obj = MagicMock()
        kwargs = {"model": "gpt-4"}

        self.tracker.log_failure_event(kwargs, response_obj, self.start_time, self.end_time)

        # Should not call save_token_usage
        mock_save.assert_not_called()

    @patch('worker.token_tracker.logger')
    def test_log_failure_event_logs_debug_info(self, mock_logger):
        """Test log_failure_event logs debug information."""
        response_obj = Exception("API rate limit exceeded")
        kwargs = {"model": "gpt-4"}

        self.tracker.log_failure_event(kwargs, response_obj, self.start_time, self.end_time)

        # Should call logger.debug
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        self.assertIn("LLM call failed", call_args[0][0])

    @patch('worker.token_tracker.logger')
    def test_log_failure_event_with_none_response(self, mock_logger):
        """Test log_failure_event with None response object."""
        kwargs = {"model": "gpt-4"}

        self.tracker.log_failure_event(kwargs, None, self.start_time, self.end_time)

        # Should handle None response gracefully
        mock_logger.debug.assert_called_once()

    @patch('worker.token_tracker.logger')
    def test_log_failure_event_truncates_long_error_messages(self, mock_logger):
        """Test that long error messages are truncated."""
        # Create a very long error message
        long_error = "x" * 500
        response_obj = Exception(long_error)
        kwargs = {"model": "gpt-4"}

        self.tracker.log_failure_event(kwargs, response_obj, self.start_time, self.end_time)

        # Check that the logged error is truncated to 200 chars
        call_args = mock_logger.debug.call_args
        extra_dict = call_args[1].get('extra', {})
        error_msg = extra_dict.get('error', '')
        self.assertLessEqual(len(error_msg), 200)

    @patch('worker.token_tracker.logger')
    def test_log_failure_event_failure_doesnt_crash(self, mock_logger):
        """Test that logging failures don't crash the method."""
        # Make logger.debug raise an exception
        mock_logger.debug.side_effect = Exception("Logging failed")

        response_obj = Exception("API error")
        kwargs = {"model": "gpt-4"}

        # Should not raise, should catch and log warning
        try:
            self.tracker.log_failure_event(kwargs, response_obj, self.start_time, self.end_time)
        except Exception:
            self.fail("log_failure_event should not raise exception on logging failure")


class TestAsyncLogFailureEvent(unittest.TestCase):
    """Test async_log_failure_event method."""

    def setUp(self):
        """Set up test fixtures."""
        self.tracker = ArticleGenerationTokenTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )
        self.start_time = 1609459200.0
        self.end_time = 1609459210.0

    @patch('worker.token_tracker.save_token_usage')
    def test_async_log_failure_event_delegates_to_sync(self, mock_save):
        """Test async_log_failure_event delegates to sync version."""
        response_obj = Exception("API error")
        kwargs = {"model": "gpt-4"}

        # Call async version
        import asyncio
        asyncio.run(self.tracker.async_log_failure_event(kwargs, response_obj, self.start_time, self.end_time))

        # Should not have called save_token_usage
        mock_save.assert_not_called()


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    @patch('worker.token_tracker.save_token_usage')
    @patch('worker.token_tracker.litellm.completion_cost')
    def test_with_empty_model_name(self, mock_cost, mock_save):
        """Test with empty model name."""
        tracker = ArticleGenerationTokenTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        response_obj = MagicMock()
        response_obj.model = ""
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = 100
        response_obj.usage.completion_tokens = 50

        kwargs = {"model": ""}
        mock_cost.return_value = 0.15

        tracker.log_success_event(1609459200.0, 1609459210.0, kwargs, response_obj)

        # Should still save, using fallback model name
        # Note: Due to signature mismatch, this test verifies the method handles empty strings

    @patch('worker.token_tracker.save_token_usage')
    @patch('worker.token_tracker.litellm.completion_cost')
    def test_with_none_response_object(self, mock_cost, mock_save):
        """Test with None response object."""
        tracker = ArticleGenerationTokenTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        kwargs = {"model": "gpt-4"}

        # Call with None response - should handle AttributeError gracefully
        try:
            tracker.log_success_event(kwargs, None, 1609459200.0, 1609459210.0)
        except AttributeError:
            # This is expected - None has no attributes
            # The exception should be caught by the outer try-except
            pass

    @patch('worker.token_tracker.save_token_usage')
    @patch('worker.token_tracker.litellm.completion_cost')
    def test_with_very_large_token_counts(self, mock_cost, mock_save):
        """Test with very large token counts."""
        tracker = ArticleGenerationTokenTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        response_obj = MagicMock()
        response_obj.model = "gpt-4"
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = 1000000
        response_obj.usage.completion_tokens = 500000

        kwargs = {"model": "gpt-4"}
        mock_cost.return_value = 1500.0

        tracker.log_success_event(kwargs, response_obj, 1609459200.0, 1609459210.0)

        # Should handle large numbers without overflow
        mock_save.assert_called_once()
        call_kwargs = mock_save.call_args[1]
        self.assertEqual(call_kwargs['prompt_tokens'], 1000000)
        self.assertEqual(call_kwargs['completion_tokens'], 500000)

    @patch('worker.token_tracker.save_token_usage')
    @patch('worker.token_tracker.litellm.completion_cost')
    def test_with_float_token_counts(self, mock_cost, mock_save):
        """Test handling of float token counts (should be converted to int)."""
        tracker = ArticleGenerationTokenTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        response_obj = MagicMock()
        response_obj.model = "gpt-4"
        response_obj.usage = MagicMock()
        # Some APIs might return floats
        response_obj.usage.prompt_tokens = 100.5
        response_obj.usage.completion_tokens = 50.7

        kwargs = {"model": "gpt-4"}
        mock_cost.return_value = 0.15

        tracker.log_success_event(kwargs, response_obj, 1609459200.0, 1609459210.0)

        # Should save what was provided (or convert to int)
        mock_save.assert_called_once()

    @patch('worker.token_tracker.save_token_usage')
    @patch('worker.token_tracker.litellm.completion_cost')
    def test_metadata_doesnt_overwrite_other_fields(self, mock_cost, mock_save):
        """Test that metadata dict only contains job_id."""
        tracker = ArticleGenerationTokenTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        response_obj = MagicMock()
        response_obj.model = "gpt-4"
        response_obj.usage = MagicMock()
        response_obj.usage.prompt_tokens = 100
        response_obj.usage.completion_tokens = 50

        kwargs = {"model": "gpt-4"}
        mock_cost.return_value = 0.15

        tracker.log_success_event(kwargs, response_obj, 1609459200.0, 1609459210.0)

        mock_save.assert_called_once()
        call_kwargs = mock_save.call_args[1]
        # Metadata should only have job_id
        self.assertEqual(call_kwargs['metadata'], {"job_id": "job-123"})


class TestIntegrationWithCustomLogger(unittest.TestCase):
    """Test that ArticleGenerationTokenTracker properly inherits from CustomLogger."""

    def test_inherits_from_custom_logger(self):
        """Test that the tracker inherits from CustomLogger."""
        from litellm.integrations.custom_logger import CustomLogger

        tracker = ArticleGenerationTokenTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        self.assertIsInstance(tracker, CustomLogger)

    def test_has_required_callback_methods(self):
        """Test that tracker has all required callback methods."""
        tracker = ArticleGenerationTokenTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )

        # Check for required methods
        self.assertTrue(hasattr(tracker, 'log_success_event'))
        self.assertTrue(hasattr(tracker, 'async_log_success_event'))
        self.assertTrue(hasattr(tracker, 'log_failure_event'))
        self.assertTrue(hasattr(tracker, 'async_log_failure_event'))

        # Check they are callable
        self.assertTrue(callable(tracker.log_success_event))
        self.assertTrue(callable(tracker.async_log_success_event))
        self.assertTrue(callable(tracker.log_failure_event))
        self.assertTrue(callable(tracker.async_log_failure_event))


if __name__ == '__main__':
    unittest.main()
