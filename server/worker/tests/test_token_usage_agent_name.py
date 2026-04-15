"""Unit tests for agent_name handling in token usage tracking.

Tests for:
- agent_name is correctly saved as tuple[0] in metadata
- Special characters and unicode in agent_name
- Multiple agents with different agent_names
- Metadata structure with agent_name and job_id
"""

import unittest
from unittest.mock import MagicMock, patch

from domain.model.token_usage import LLMCallResult
from services.token_usage_service import track_agent_usage


class TestAgentNameHandling(unittest.TestCase):
    """Test cases for agent_name handling in track_agent_usage."""

    def setUp(self):
        """Set up test fixtures."""
        self.user_id = "test-user-123"
        self.article_id = "article-456"
        self.job_id = "job-789"

    def test_agent_name_is_saved_when_provided(self):
        """Test that agent_name from tuple is saved to database."""
        agent_usage = [
            ('Article Search', LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.001,
            ))
        ]

        with patch('services.token_usage_service.logger'):
            mock_repo = MagicMock()
            track_agent_usage(
                mock_repo,
                agent_usage,
                self.user_id,
                self.article_id,
                self.job_id,
            )

            usage = mock_repo.save.call_args[0][0]
            self.assertIn('agent_name', usage.metadata)
            self.assertEqual(usage.metadata['agent_name'], 'Article Search')

    def test_agent_name_with_special_characters(self):
        """Test that agent_name with special characters is preserved."""
        agent_usage = [
            ('Quality Check #2 (Advanced)', LLMCallResult(
                model='gpt-4',
                prompt_tokens=200,
                completion_tokens=100,
                total_tokens=300,
                estimated_cost=0.001,
            ))
        ]

        with patch('services.token_usage_service.logger'):
            mock_repo = MagicMock()
            track_agent_usage(
                mock_repo,
                agent_usage,
                self.user_id,
                self.article_id,
                self.job_id,
            )

            usage = mock_repo.save.call_args[0][0]
            self.assertEqual(usage.metadata['agent_name'], 'Quality Check #2 (Advanced)')

    def test_agent_name_with_unicode_characters(self):
        """Test that agent_name with unicode characters is preserved."""
        agent_usage = [
            ('Recherche \U0001f4f0 Fran\u00e7aise', LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.001,
            ))
        ]

        with patch('services.token_usage_service.logger'):
            mock_repo = MagicMock()
            track_agent_usage(
                mock_repo,
                agent_usage,
                self.user_id,
                self.article_id,
                self.job_id,
            )

            usage = mock_repo.save.call_args[0][0]
            self.assertEqual(usage.metadata['agent_name'], 'Recherche \U0001f4f0 Fran\u00e7aise')

    def test_agent_name_priority_over_agent_role(self):
        """Test that agent_name provided in tuple is saved to metadata."""
        agent_usage = [
            ('Short Name', LLMCallResult(
                model='gpt-4',
                prompt_tokens=200,
                completion_tokens=100,
                total_tokens=300,
                estimated_cost=0.001,
            ))
        ]

        with patch('services.token_usage_service.logger'):
            mock_repo = MagicMock()
            track_agent_usage(
                mock_repo,
                agent_usage,
                self.user_id,
                self.article_id,
                self.job_id,
            )

            usage = mock_repo.save.call_args[0][0]
            self.assertEqual(usage.metadata['agent_name'], 'Short Name')

    def test_agent_name_with_leading_trailing_whitespace(self):
        """Test that agent_name with whitespace is preserved as-is."""
        agent_usage = [
            ('  Article Search  ', LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.001,
            ))
        ]

        with patch('services.token_usage_service.logger'):
            mock_repo = MagicMock()
            track_agent_usage(
                mock_repo,
                agent_usage,
                self.user_id,
                self.article_id,
                self.job_id,
            )

            usage = mock_repo.save.call_args[0][0]
            self.assertEqual(usage.metadata['agent_name'], '  Article Search  ')

    def test_multiple_agents_different_agent_names(self):
        """Test multiple agents with different agent_name values."""
        agent_usage = [
            ('Article Search', LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.001,
            )),
            ('Writer', LLMCallResult(
                model='gpt-4',
                prompt_tokens=200,
                completion_tokens=100,
                total_tokens=300,
                estimated_cost=0.001,
            )),
            ('Quality Check', LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=75,
                completion_tokens=25,
                total_tokens=100,
                estimated_cost=0.001,
            ))
        ]

        with patch('services.token_usage_service.logger'):
            mock_repo = MagicMock()
            track_agent_usage(
                mock_repo,
                agent_usage,
                self.user_id,
                self.article_id,
                self.job_id,
            )

            self.assertEqual(mock_repo.save.call_count, 3)
            calls = mock_repo.save.call_args_list

            self.assertEqual(calls[0][0][0].metadata['agent_name'], 'Article Search')
            self.assertEqual(calls[1][0][0].metadata['agent_name'], 'Writer')
            self.assertEqual(calls[2][0][0].metadata['agent_name'], 'Quality Check')

    def test_agent_name_with_very_long_string(self):
        """Test that very long agent_name is preserved."""
        long_name = 'A' * 500
        agent_usage = [
            (long_name, LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.001,
            ))
        ]

        with patch('services.token_usage_service.logger'):
            mock_repo = MagicMock()
            track_agent_usage(
                mock_repo,
                agent_usage,
                self.user_id,
                self.article_id,
                self.job_id,
            )

            usage = mock_repo.save.call_args[0][0]
            self.assertEqual(usage.metadata['agent_name'], long_name)

    def test_agent_name_metadata_structure(self):
        """Test that agent_name is properly placed in metadata dict."""
        agent_usage = [
            ('Article Search', LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.001,
            ))
        ]

        with patch('services.token_usage_service.logger'):
            mock_repo = MagicMock()
            track_agent_usage(
                mock_repo,
                agent_usage,
                self.user_id,
                self.article_id,
                self.job_id,
            )

            usage = mock_repo.save.call_args[0][0]
            metadata = usage.metadata

            self.assertIn('job_id', metadata)
            self.assertIn('agent_name', metadata)
            self.assertEqual(metadata['job_id'], self.job_id)
            self.assertEqual(metadata['agent_name'], 'Article Search')

    def test_agent_name_not_overwriting_job_id(self):
        """Test that agent_name and job_id coexist in metadata."""
        agent_usage = [
            ('Article Search', LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.001,
            ))
        ]

        with patch('services.token_usage_service.logger'):
            mock_repo = MagicMock()
            track_agent_usage(
                mock_repo,
                agent_usage,
                self.user_id,
                self.article_id,
                self.job_id,
            )

            usage = mock_repo.save.call_args[0][0]
            metadata = usage.metadata

            self.assertEqual(len(metadata), 2)
            self.assertEqual(metadata['job_id'], self.job_id)
            self.assertEqual(metadata['agent_name'], 'Article Search')


if __name__ == '__main__':
    unittest.main()
