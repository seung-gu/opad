"""Unit tests for token_usage module agent usage tracking.

Tests for:
- track_agent_usage() function with agent usage data
- Edge cases: unknown models, zero tokens, empty agent lists
- Error handling and non-fatal exceptions
"""

import unittest
from unittest.mock import patch, MagicMock

from domain.model.token_usage import LLMCallResult
from services.token_usage_service import track_agent_usage


class TestTrackAgentUsage(unittest.TestCase):
    """Test cases for track_agent_usage function."""

    def setUp(self):
        """Set up test fixtures."""
        self.user_id = "test-user-123"
        self.article_id = "article-456"
        self.job_id = "job-789"

    def test_track_agent_usage_with_single_agent(self):
        """Test saving token usage for single agent with agent_name."""
        agent_usage = [
            ('Article Search', LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.001,
            ))
        ]

        with patch('services.token_usage_service.logger') as mock_logger:
            mock_repo = MagicMock()
            track_agent_usage(
                mock_repo,
                agent_usage,
                self.user_id,
                self.article_id,
                self.job_id,
            )

            mock_repo.save.assert_called_once()
            usage = mock_repo.save.call_args[0][0]

            self.assertEqual(usage.user_id, self.user_id)
            self.assertEqual(usage.operation, 'article_generation')
            self.assertEqual(usage.model, 'gpt-4.1-mini')
            self.assertEqual(usage.prompt_tokens, 100)
            self.assertEqual(usage.completion_tokens, 50)
            self.assertEqual(usage.estimated_cost, 0.001)
            self.assertEqual(usage.article_id, self.article_id)
            self.assertEqual(usage.metadata['job_id'], self.job_id)
            self.assertEqual(usage.metadata['agent_name'], 'Article Search')

            self.assertEqual(mock_logger.info.call_count, 2)

    def test_track_agent_usage_with_multiple_agents(self):
        """Test saving token usage for multiple agents with agent_name."""
        agent_usage = [
            ('Article Search', LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.001,
            )),
            ('Article Selection', LLMCallResult(
                model='gpt-4',
                prompt_tokens=500,
                completion_tokens=250,
                total_tokens=750,
                estimated_cost=0.010,
            )),
            ('Quality Reviewer', LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=75,
                completion_tokens=25,
                total_tokens=100,
                estimated_cost=0.0008,
            ))
        ]

        with patch('services.token_usage_service.logger') as mock_logger:
            mock_repo = MagicMock()
            track_agent_usage(
                mock_repo,
                agent_usage,
                self.user_id,
                self.article_id,
                self.job_id,
            )

            self.assertEqual(mock_repo.save.call_count, 3)

            self.assertEqual(mock_logger.info.call_count, 2)
            log_extra = mock_logger.info.call_args[1]['extra']
            self.assertEqual(log_extra['agentCount'], 3)

            calls = mock_repo.save.call_args_list
            self.assertEqual(calls[0][0][0].metadata['agent_name'], 'Article Search')
            self.assertEqual(calls[1][0][0].metadata['agent_name'], 'Article Selection')
            self.assertEqual(calls[2][0][0].metadata['agent_name'], 'Quality Reviewer')

    def test_track_agent_usage_skips_zero_token_agents(self):
        """Test that agents with zero tokens are skipped."""
        agent_usage = [
            ('News Researcher', LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.001,
            )),
            ('Article Writer', LLMCallResult(
                model='gpt-4',
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                estimated_cost=0.0,
            )),
            ('Quality Reviewer', LLMCallResult(
                model='claude-3-sonnet',
                prompt_tokens=50,
                completion_tokens=25,
                total_tokens=75,
                estimated_cost=0.0005,
            ))
        ]

        with patch('services.token_usage_service.logger') as mock_logger:
            mock_repo = MagicMock()
            track_agent_usage(
                mock_repo,
                agent_usage,
                self.user_id,
                self.article_id,
                self.job_id,
            )

            self.assertEqual(mock_repo.save.call_count, 2)

            log_extra = mock_logger.info.call_args[1]['extra']
            self.assertEqual(log_extra['agentCount'], 2)

    def test_track_agent_usage_with_empty_agent_list(self):
        """Test saving token usage with empty agent list."""
        agent_usage = []

        with patch('services.token_usage_service.logger') as mock_logger:
            mock_repo = MagicMock()
            track_agent_usage(
                mock_repo,
                agent_usage,
                self.user_id,
                self.article_id,
                self.job_id,
            )

            mock_repo.save.assert_not_called()

            self.assertEqual(mock_logger.info.call_count, 2)
            log_extra = mock_logger.info.call_args[1]['extra']
            self.assertEqual(log_extra['agentCount'], 0)

    def test_track_agent_usage_with_none_article_id(self):
        """Test saving token usage with None article_id."""
        agent_usage = [
            ('News Researcher', LLMCallResult(
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
                None,
                self.job_id,
            )

            usage = mock_repo.save.call_args[0][0]
            self.assertIsNone(usage.article_id)

    def test_track_agent_usage_stores_estimated_cost_from_llm_call_result(self):
        """Test that estimated_cost from LLMCallResult is stored correctly for each agent."""
        agent_usage = [
            ('News Researcher', LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.001,
            )),
            ('Article Writer', LLMCallResult(
                model='gpt-4',
                prompt_tokens=200,
                completion_tokens=100,
                total_tokens=300,
                estimated_cost=0.01,
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

            calls = mock_repo.save.call_args_list
            self.assertEqual(calls[0][0][0].estimated_cost, 0.001)
            self.assertEqual(calls[1][0][0].estimated_cost, 0.01)

    def test_track_agent_usage_logs_job_metadata(self):
        """Test that job metadata is logged correctly."""
        agent_usage = [
            ('News Researcher', LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.001,
            ))
        ]

        with patch('services.token_usage_service.logger') as mock_logger:
            mock_repo = MagicMock()
            track_agent_usage(
                mock_repo,
                agent_usage,
                self.user_id,
                self.article_id,
                self.job_id,
            )

            self.assertEqual(mock_logger.info.call_count, 2)
            call_args = mock_logger.info.call_args

            self.assertIn("Token usage saved", call_args[0][0])

            extra = call_args[1]['extra']
            self.assertEqual(extra['jobId'], self.job_id)
            self.assertEqual(extra['articleId'], self.article_id)
            self.assertEqual(extra['agentCount'], 1)

    def test_track_agent_usage_exception_logged_as_warning(self):
        """Test that exceptions during save are logged as warning (non-fatal)."""
        with patch('services.token_usage_service.logger') as mock_logger:
            mock_repo = MagicMock()
            track_agent_usage(
                mock_repo,
                None,  # Will cause TypeError when iterating
                self.user_id,
                self.article_id,
                self.job_id,
            )

            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args

            self.assertIn("Failed to save token usage", call_args[0][0])

            extra = call_args[1]['extra']
            self.assertEqual(extra['jobId'], self.job_id)
            self.assertIn("TypeError", extra['errorType'])

    def test_track_agent_usage_save_token_usage_exception_non_fatal(self):
        """Test that exception in save_token_usage doesn't crash function."""
        agent_usage = [
            ('News Researcher', LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.001,
            ))
        ]

        with patch('services.token_usage_service.logger') as mock_logger:
            mock_repo = MagicMock()
            mock_repo.save.side_effect = ValueError("DB error")
            track_agent_usage(
                mock_repo,
                agent_usage,
                self.user_id,
                self.article_id,
                self.job_id,
            )

            mock_logger.warning.assert_called_once()
            extra = mock_logger.warning.call_args[1]['extra']
            self.assertIn("ValueError", extra['errorType'])

    def test_track_agent_usage_with_all_agents_zero_tokens(self):
        """Test when all agents have zero tokens."""
        agent_usage = [
            ('unknown', LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                estimated_cost=0.0,
            )),
            ('unknown', LLMCallResult(
                model='gpt-4',
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                estimated_cost=0.0,
            ))
        ]

        with patch('services.token_usage_service.logger') as mock_logger:
            mock_repo = MagicMock()
            track_agent_usage(
                mock_repo,
                agent_usage,
                self.user_id,
                self.article_id,
                self.job_id,
            )

            mock_repo.save.assert_not_called()

            log_extra = mock_logger.info.call_args[1]['extra']
            self.assertEqual(log_extra['agentCount'], 0)

    def test_track_agent_usage_mixed_zero_and_nonzero_tokens(self):
        """Test with mix of zero and non-zero token agents."""
        agent_usage = [
            ('Agent 1', LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                estimated_cost=0.0,
            )),
            ('Agent 2', LLMCallResult(
                model='gpt-4',
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.001,
            )),
            ('Agent 3', LLMCallResult(
                model='claude-3-sonnet',
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                estimated_cost=0.0,
            )),
            ('Agent 4', LLMCallResult(
                model='claude-3-opus',
                prompt_tokens=200,
                completion_tokens=100,
                total_tokens=300,
                estimated_cost=0.005,
            ))
        ]

        with patch('services.token_usage_service.logger') as mock_logger:
            mock_repo = MagicMock()
            track_agent_usage(
                mock_repo,
                agent_usage,
                self.user_id,
                self.article_id,
                self.job_id,
            )

            self.assertEqual(mock_repo.save.call_count, 2)

            log_extra = mock_logger.info.call_args[1]['extra']
            self.assertEqual(log_extra['agentCount'], 2)

    def test_track_agent_usage_passes_job_id_in_metadata(self):
        """Test that job_id is included in metadata passed to save_token_usage."""
        agent_usage = [
            ('Test Name', LLMCallResult(
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
            self.assertIsNotNone(usage.metadata)
            self.assertEqual(usage.metadata['job_id'], self.job_id)

    def test_track_agent_usage_operation_type_is_article_generation(self):
        """Test that operation type is always 'article_generation'."""
        agent_usage = [
            ('Test Name', LLMCallResult(
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
            self.assertEqual(usage.operation, 'article_generation')

    def test_track_agent_usage_with_different_models(self):
        """Test saving usage with different model types."""
        agent_usage = [
            ('Researcher', LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.001,
            )),
            ('Writer', LLMCallResult(
                model='claude-3-sonnet-20240229',
                prompt_tokens=200,
                completion_tokens=100,
                total_tokens=300,
                estimated_cost=0.003,
            )),
            ('Reviewer', LLMCallResult(
                model='gemini-1.5-flash',
                prompt_tokens=150,
                completion_tokens=75,
                total_tokens=225,
                estimated_cost=0.002,
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
            models = [
                mock_repo.save.call_args_list[0][0][0].model,
                mock_repo.save.call_args_list[1][0][0].model,
                mock_repo.save.call_args_list[2][0][0].model
            ]
            self.assertIn('gpt-4.1-mini', models)
            self.assertIn('claude-3-sonnet-20240229', models)
            self.assertIn('gemini-1.5-flash', models)

    def test_track_agent_usage_agent_name_stored_from_tuple(self):
        """Test that agent_name from tuple is stored in metadata."""
        agent_usage = [
            ('Article Researcher', LLMCallResult(
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
            self.assertEqual(usage.metadata['agent_name'], 'Article Researcher')

    def test_track_agent_usage_agent_name_with_special_characters(self):
        """Test that agent_name with special characters is preserved."""
        agent_usage = [
            ('Quality Check #2', LLMCallResult(
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
            self.assertEqual(usage.metadata['agent_name'], 'Quality Check #2')

    def test_track_agent_usage_metadata_includes_job_id_and_agent_name(self):
        """Test that metadata includes both job_id and agent_name."""
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

    def test_track_agent_usage_logs_agent_names_in_usage_data(self):
        """Test that agent usage logging includes agent name, model, and tokens."""
        agent_usage = [
            ('Article Search', LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.001,
            )),
            ('Article Writer', LLMCallResult(
                model='gpt-4',
                prompt_tokens=500,
                completion_tokens=250,
                total_tokens=750,
                estimated_cost=0.01,
            ))
        ]

        with patch('services.token_usage_service.logger') as mock_logger:
            mock_repo = MagicMock()
            track_agent_usage(
                mock_repo,
                agent_usage,
                self.user_id,
                self.article_id,
                self.job_id,
            )

            first_info_call = mock_logger.info.call_args_list[0]
            extra = first_info_call[1]['extra']
            self.assertIn('usageData', extra)
            usage_data = extra['usageData']
            self.assertEqual(len(usage_data), 2)
            self.assertEqual(usage_data[0]['name'], 'Article Search')
            self.assertEqual(usage_data[0]['model'], 'gpt-4.1-mini')
            self.assertEqual(usage_data[0]['tokens'], 150)
            self.assertEqual(usage_data[1]['name'], 'Article Writer')
            self.assertEqual(usage_data[1]['model'], 'gpt-4')
            self.assertEqual(usage_data[1]['tokens'], 750)

    def test_track_agent_usage_cost_from_llm_call_result(self):
        """Test that cost from LLMCallResult is used directly."""
        agent_usage = [
            ('Test', LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.0042,
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
            self.assertEqual(usage.estimated_cost, 0.0042)


class TestEstimateCostIntegration(unittest.TestCase):
    """Integration tests for track_agent_usage saving LLMCallResult data."""

    def test_track_agent_usage_saves_llm_call_result_data(self):
        """Test that track_agent_usage correctly saves all LLMCallResult fields."""
        agent_usage = [
            ('Integration Test', LLMCallResult(
                model='gpt-4.1-mini',
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost=0.003,
            ))
        ]

        with patch('services.token_usage_service.logger'):
            mock_repo = MagicMock()
            track_agent_usage(
                mock_repo,
                agent_usage,
                "user-123",
                "article-456",
                "job-789",
            )

            usage = mock_repo.save.call_args[0][0]
            self.assertEqual(usage.model, 'gpt-4.1-mini')
            self.assertEqual(usage.prompt_tokens, 100)
            self.assertEqual(usage.completion_tokens, 50)
            self.assertEqual(usage.total_tokens, 150)
            self.assertEqual(usage.estimated_cost, 0.003)
            self.assertEqual(usage.metadata['agent_name'], 'Integration Test')
            self.assertEqual(usage.metadata['job_id'], 'job-789')
            self.assertEqual(usage.user_id, 'user-123')
            self.assertEqual(usage.article_id, 'article-456')
            self.assertEqual(usage.operation, 'article_generation')


if __name__ == '__main__':
    unittest.main()
