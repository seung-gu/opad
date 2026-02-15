"""Unit tests for token_usage module cost calculation and crew tracking.

Tests for:
- calculate_cost() function with various models and token counts
- save_crew_token_usage() function with CrewAI results
- Edge cases: unknown models, zero tokens, empty agent lists
- Error handling and non-fatal exceptions
"""

import unittest
from unittest.mock import Mock, patch, MagicMock

from utils.token_usage import calculate_cost, save_crew_token_usage


class TestCalculateCost(unittest.TestCase):
    """Test cases for calculate_cost function."""

    def test_calculate_cost_with_valid_openai_model(self):
        """Test cost calculation with valid OpenAI model."""
        with patch('litellm.cost_per_token') as mock_cost:
            mock_cost.return_value = (0.001, 0.002)

            cost = calculate_cost('gpt-4.1-mini', 100, 50)

            self.assertEqual(cost, 0.003)
            mock_cost.assert_called_once_with(
                model='gpt-4.1-mini',
                prompt_tokens=100,
                completion_tokens=50
            )

    def test_calculate_cost_with_valid_gpt4_model(self):
        """Test cost calculation with gpt-4 model."""
        with patch('litellm.cost_per_token') as mock_cost:
            mock_cost.return_value = (0.003, 0.006)

            cost = calculate_cost('gpt-4', 500, 250)

            self.assertAlmostEqual(cost, 0.009, places=10)
            mock_cost.assert_called_once()

    def test_calculate_cost_with_zero_prompt_tokens(self):
        """Test cost calculation with zero prompt tokens."""
        with patch('litellm.cost_per_token') as mock_cost:
            mock_cost.return_value = (0.0, 0.001)

            cost = calculate_cost('gpt-4.1-mini', 0, 100)

            self.assertEqual(cost, 0.001)

    def test_calculate_cost_with_zero_completion_tokens(self):
        """Test cost calculation with zero completion tokens."""
        with patch('litellm.cost_per_token') as mock_cost:
            mock_cost.return_value = (0.002, 0.0)

            cost = calculate_cost('gpt-4.1-mini', 200, 0)

            self.assertEqual(cost, 0.002)

    def test_calculate_cost_with_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        with patch('litellm.cost_per_token') as mock_cost:
            mock_cost.return_value = (0.0, 0.0)

            cost = calculate_cost('gpt-4.1-mini', 0, 0)

            self.assertEqual(cost, 0.0)

    def test_calculate_cost_with_large_token_count(self):
        """Test cost calculation with very large token counts."""
        with patch('litellm.cost_per_token') as mock_cost:
            mock_cost.return_value = (1.5, 3.0)

            cost = calculate_cost('gpt-4', 100000, 50000)

            self.assertEqual(cost, 4.5)

    def test_calculate_cost_with_very_small_cost(self):
        """Test cost calculation returning very small cost."""
        with patch('litellm.cost_per_token') as mock_cost:
            mock_cost.return_value = (0.00001, 0.00002)

            cost = calculate_cost('gpt-4.1-mini', 10, 5)

            self.assertAlmostEqual(cost, 0.00003, places=8)

    def test_calculate_cost_unknown_model_key_error(self):
        """Test that KeyError for unknown model returns 0.0."""
        with patch('litellm.cost_per_token') as mock_cost:
            mock_cost.side_effect = KeyError("Model not found")

            cost = calculate_cost('unknown-model-xyz', 100, 50)

            self.assertEqual(cost, 0.0)

    def test_calculate_cost_unknown_model_value_error(self):
        """Test that ValueError for invalid model returns 0.0."""
        with patch('litellm.cost_per_token') as mock_cost:
            mock_cost.side_effect = ValueError("Invalid model")

            cost = calculate_cost('invalid-model', 100, 50)

            self.assertEqual(cost, 0.0)

    def test_calculate_cost_attribute_error(self):
        """Test that AttributeError returns 0.0."""
        with patch('litellm.cost_per_token') as mock_cost:
            mock_cost.side_effect = AttributeError("Missing attribute")

            cost = calculate_cost('bad-model', 100, 50)

            self.assertEqual(cost, 0.0)

    def test_calculate_cost_unexpected_exception_logs_debug(self):
        """Test that unexpected exception is caught and logged at debug level."""
        with patch('litellm.cost_per_token') as mock_cost:
            with patch('utils.token_usage.logger') as mock_logger:
                mock_cost.side_effect = RuntimeError("Unexpected error")

                cost = calculate_cost('gpt-4.1-mini', 100, 50)

                self.assertEqual(cost, 0.0)
                mock_logger.debug.assert_called_once()
                args = mock_logger.debug.call_args[0]
                self.assertIn("Unexpected error", str(args))
                self.assertIn("gpt-4.1-mini", str(args))

    def test_calculate_cost_import_error_on_litellm_missing(self):
        """Test handling when litellm.cost_per_token raises AttributeError."""
        # Simulate missing attribute by raising AttributeError
        with patch('litellm.cost_per_token') as mock_cost:
            mock_cost.side_effect = AttributeError("module has no attribute")
            with patch('utils.token_usage.logger'):
                cost = calculate_cost('gpt-4.1-mini', 100, 50)
                self.assertEqual(cost, 0.0)

    def test_calculate_cost_returns_float(self):
        """Test that calculate_cost always returns a float."""
        with patch('litellm.cost_per_token') as mock_cost:
            mock_cost.return_value = (0.001, 0.002)

            cost = calculate_cost('gpt-4.1-mini', 100, 50)

            self.assertIsInstance(cost, float)

    def test_calculate_cost_with_float_token_values(self):
        """Test cost calculation when tokens are passed as floats."""
        with patch('litellm.cost_per_token') as mock_cost:
            mock_cost.return_value = (0.001, 0.002)

            # Even though we pass floats, the function should handle them
            cost = calculate_cost('gpt-4.1-mini', 100.5, 50.5)

            self.assertEqual(cost, 0.003)
            # Verify the values were passed as-is
            call_kwargs = mock_cost.call_args[1]
            self.assertEqual(call_kwargs['prompt_tokens'], 100.5)
            self.assertEqual(call_kwargs['completion_tokens'], 50.5)

    def test_calculate_cost_negative_tokens_still_calls_litellm(self):
        """Test that negative tokens are still passed to litellm (no validation in calculate_cost)."""
        with patch('litellm.cost_per_token') as mock_cost:
            mock_cost.return_value = (0.0, 0.0)

            cost = calculate_cost('gpt-4.1-mini', -100, -50)

            self.assertEqual(cost, 0.0)
            # Verify negative values were passed
            call_kwargs = mock_cost.call_args[1]
            self.assertEqual(call_kwargs['prompt_tokens'], -100)
            self.assertEqual(call_kwargs['completion_tokens'], -50)


class TestSaveCrewTokenUsage(unittest.TestCase):
    """Test cases for save_crew_token_usage function."""

    def setUp(self):
        """Set up test fixtures."""
        self.user_id = "test-user-123"
        self.article_id = "article-456"
        self.job_id = "job-789"

    def test_save_crew_token_usage_with_single_agent(self):
        """Test saving token usage for single agent with agent_name."""
        # Create mock CrewResult
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'News Researcher',
                'agent_name': 'Article Search',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger') as mock_logger:
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                # Verify save_token_usage was called once
                mock_repo.save.assert_called_once()
                call_kwargs = mock_repo.save.call_args[1]

                # Verify correct parameters
                self.assertEqual(call_kwargs['user_id'], self.user_id)
                self.assertEqual(call_kwargs['operation'], 'article_generation')
                self.assertEqual(call_kwargs['model'], 'gpt-4.1-mini')
                self.assertEqual(call_kwargs['prompt_tokens'], 100)
                self.assertEqual(call_kwargs['completion_tokens'], 50)
                self.assertEqual(call_kwargs['estimated_cost'], 0.001)
                self.assertEqual(call_kwargs['article_id'], self.article_id)
                self.assertEqual(call_kwargs['metadata']['job_id'], self.job_id)
                # agent_name should be used when available
                self.assertEqual(call_kwargs['metadata']['agent_name'], 'Article Search')

                # Verify logger was called twice (debug + final)
                self.assertEqual(mock_logger.info.call_count, 2)

    def test_save_crew_token_usage_with_multiple_agents(self):
        """Test saving token usage for multiple agents with agent_name."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'News Researcher',
                'agent_name': 'Article Search',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            },
            {
                'agent_role': 'Article Writer',
                'agent_name': 'Article Selection',
                'model': 'gpt-4',
                'prompt_tokens': 500,
                'completion_tokens': 250,
                'total_tokens': 750
            },
            {
                'agent_role': 'Quality Reviewer',
                'agent_name': None,  # Falls back to agent_role
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 75,
                'completion_tokens': 25,
                'total_tokens': 100
            }
        ]

        with patch('utils.token_usage.calculate_cost') as mock_calculate:
            mock_calculate.side_effect = [0.001, 0.010, 0.0008]
            with patch('utils.token_usage.logger') as mock_logger:
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                # Verify save_token_usage was called 3 times
                self.assertEqual(mock_repo.save.call_count, 3)

                # Verify logger shows 3 agents saved
                self.assertEqual(mock_logger.info.call_count, 2)
                log_extra = mock_logger.info.call_args[1]['extra']
                self.assertEqual(log_extra['agentCount'], 3)

                # Verify agent_name or fallback to agent_role in metadata
                calls = mock_repo.save.call_args_list
                self.assertEqual(calls[0][1]['metadata']['agent_name'], 'Article Search')
                self.assertEqual(calls[1][1]['metadata']['agent_name'], 'Article Selection')
                self.assertEqual(calls[2][1]['metadata']['agent_name'], 'Quality Reviewer')  # Falls back

    def test_save_crew_token_usage_skips_zero_token_agents(self):
        """Test that agents with zero tokens are skipped."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'News Researcher',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            },
            {
                'agent_role': 'Article Writer',
                'model': 'gpt-4',
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0  # This should be skipped
            },
            {
                'agent_role': 'Quality Reviewer',
                'model': 'claude-3-sonnet',
                'prompt_tokens': 50,
                'completion_tokens': 25,
                'total_tokens': 75
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger') as mock_logger:
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                # Verify save_token_usage was called only 2 times (skipped zero-token agent)
                self.assertEqual(mock_repo.save.call_count, 2)

                # Verify logger shows 2 agents saved
                log_extra = mock_logger.info.call_args[1]['extra']
                self.assertEqual(log_extra['agentCount'], 2)

    def test_save_crew_token_usage_with_empty_agent_list(self):
        """Test saving token usage with empty agent list."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = []

        with patch('utils.token_usage.calculate_cost'):
            with patch('utils.token_usage.logger') as mock_logger:
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                # Verify save_token_usage was not called
                mock_repo.save.assert_not_called()

                # Verify logger still logged (with 0 agents)
                self.assertEqual(mock_logger.info.call_count, 2)
                log_extra = mock_logger.info.call_args[1]['extra']
                self.assertEqual(log_extra['agentCount'], 0)

    def test_save_crew_token_usage_with_none_article_id(self):
        """Test saving token usage with None article_id."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'News Researcher',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    None,  # article_id is None
                    self.job_id,
                    repo=mock_repo
                )

                # Verify article_id is passed as None
                call_kwargs = mock_repo.save.call_args[1]
                self.assertIsNone(call_kwargs['article_id'])

    def test_save_crew_token_usage_calculates_cost_for_each_agent(self):
        """Test that cost is calculated for each agent's model and tokens."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'News Researcher',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            },
            {
                'agent_role': 'Article Writer',
                'model': 'gpt-4',
                'prompt_tokens': 200,
                'completion_tokens': 100,
                'total_tokens': 300
            }
        ]

        with patch('utils.token_usage.calculate_cost') as mock_calculate:
            mock_calculate.side_effect = [0.001, 0.01]
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                # Verify calculate_cost was called for each agent
                self.assertEqual(mock_calculate.call_count, 2)

                # Verify correct model and token counts
                calls = mock_calculate.call_args_list
                self.assertEqual(calls[0][1]['model'], 'gpt-4.1-mini')
                self.assertEqual(calls[0][1]['prompt_tokens'], 100)
                self.assertEqual(calls[0][1]['completion_tokens'], 50)

                self.assertEqual(calls[1][1]['model'], 'gpt-4')
                self.assertEqual(calls[1][1]['prompt_tokens'], 200)
                self.assertEqual(calls[1][1]['completion_tokens'], 100)

    def test_save_crew_token_usage_logs_job_metadata(self):
        """Test that job metadata is logged correctly."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'News Researcher',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger') as mock_logger:
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                # Verify logger.info was called
                self.assertEqual(mock_logger.info.call_count, 2)
                call_args = mock_logger.info.call_args

                # Check message
                self.assertIn("Token usage saved", call_args[0][0])

                # Check extra metadata
                extra = call_args[1]['extra']
                self.assertEqual(extra['jobId'], self.job_id)
                self.assertEqual(extra['articleId'], self.article_id)
                self.assertEqual(extra['agentCount'], 1)

    def test_save_crew_token_usage_exception_logged_as_warning(self):
        """Test that exceptions during save are logged as warning (non-fatal)."""
        mock_result = Mock()
        mock_result.get_agent_usage.side_effect = RuntimeError("Failed to get agent usage")

        with patch('utils.token_usage.logger') as mock_logger:
            mock_repo = MagicMock()
            # Should not raise exception
            save_crew_token_usage(
                mock_result,
                self.user_id,
                self.article_id,
                self.job_id,
                repo=mock_repo
            )

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args

            # Check message
            self.assertIn("Failed to save token usage", call_args[0][0])

            # Check extra metadata includes error info
            extra = call_args[1]['extra']
            self.assertEqual(extra['jobId'], self.job_id)
            self.assertIn("RuntimeError", extra['errorType'])

    def test_save_crew_token_usage_save_token_usage_exception_non_fatal(self):
        """Test that exception in save_token_usage doesn't crash function."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'News Researcher',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger') as mock_logger:
                mock_repo = MagicMock()
                mock_repo.save.side_effect = ValueError("DB error")
                # Should not raise exception
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                # Verify warning was logged with error info
                mock_logger.warning.assert_called_once()
                extra = mock_logger.warning.call_args[1]['extra']
                self.assertIn("ValueError", extra['errorType'])

    def test_save_crew_token_usage_with_all_agents_zero_tokens(self):
        """Test when all agents have zero tokens."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            },
            {
                'model': 'gpt-4',
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            }
        ]

        with patch('utils.token_usage.logger') as mock_logger:
            mock_repo = MagicMock()
            save_crew_token_usage(
                mock_result,
                self.user_id,
                self.article_id,
                self.job_id,
                repo=mock_repo
            )

            # Verify no saves (all skipped)
            mock_repo.save.assert_not_called()

            # Verify logger shows 0 agents saved
            log_extra = mock_logger.info.call_args[1]['extra']
            self.assertEqual(log_extra['agentCount'], 0)

    def test_save_crew_token_usage_mixed_zero_and_nonzero_tokens(self):
        """Test with mix of zero and non-zero token agents."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Agent 1',
                'agent_name': None,
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            },
            {
                'agent_role': 'Agent 2',
                'agent_name': None,
                'model': 'gpt-4',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            },
            {
                'agent_role': 'Agent 3',
                'agent_name': None,
                'model': 'claude-3-sonnet',
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            },
            {
                'agent_role': 'Agent 4',
                'agent_name': None,
                'model': 'claude-3-opus',
                'prompt_tokens': 200,
                'completion_tokens': 100,
                'total_tokens': 300
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger') as mock_logger:
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                # Verify only non-zero agents were saved (2 out of 4)
                self.assertEqual(mock_repo.save.call_count, 2)

                # Verify logger shows 2 agents saved
                log_extra = mock_logger.info.call_args[1]['extra']
                self.assertEqual(log_extra['agentCount'], 2)

    def test_save_crew_token_usage_passes_job_id_in_metadata(self):
        """Test that job_id is included in metadata passed to save_token_usage."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Test Agent',
                'agent_name': 'Test Name',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                self.assertIn('metadata', call_kwargs)
                self.assertEqual(call_kwargs['metadata']['job_id'], self.job_id)

    def test_save_crew_token_usage_operation_type_is_article_generation(self):
        """Test that operation type is always 'article_generation'."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Test Agent',
                'agent_name': 'Test Name',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                self.assertEqual(call_kwargs['operation'], 'article_generation')

    def test_save_crew_token_usage_with_different_models(self):
        """Test saving usage with different model types."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Researcher',
                'agent_name': None,
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            },
            {
                'agent_role': 'Writer',
                'agent_name': None,
                'model': 'claude-3-sonnet-20240229',
                'prompt_tokens': 200,
                'completion_tokens': 100,
                'total_tokens': 300
            },
            {
                'agent_role': 'Reviewer',
                'agent_name': None,
                'model': 'gemini-1.5-flash',
                'prompt_tokens': 150,
                'completion_tokens': 75,
                'total_tokens': 225
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                # Verify all 3 were saved with correct models
                self.assertEqual(mock_repo.save.call_count, 3)
                models = [
                    mock_repo.save.call_args_list[0][1]['model'],
                    mock_repo.save.call_args_list[1][1]['model'],
                    mock_repo.save.call_args_list[2][1]['model']
                ]
                self.assertIn('gpt-4.1-mini', models)
                self.assertIn('claude-3-sonnet-20240229', models)
                self.assertIn('gemini-1.5-flash', models)

    def test_save_crew_token_usage_agent_name_fallback_to_agent_role(self):
        """Test that agent_name falls back to agent_role when agent_name is None."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Article Researcher',
                'agent_name': None,  # No agent_name
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                # Should fall back to agent_role
                self.assertEqual(call_kwargs['metadata']['agent_name'], 'Article Researcher')

    def test_save_crew_token_usage_agent_name_empty_string_fallback(self):
        """Test that empty string agent_name falls back to agent_role."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Content Writer',
                'agent_name': '',  # Empty string
                'model': 'gpt-4',
                'prompt_tokens': 200,
                'completion_tokens': 100,
                'total_tokens': 300
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                # Empty string is falsy, should fall back to agent_role
                self.assertEqual(call_kwargs['metadata']['agent_name'], 'Content Writer')

    def test_save_crew_token_usage_agent_name_with_special_characters(self):
        """Test that agent_name with special characters is preserved."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Reviewer (Advanced)',
                'agent_name': 'Quality Check #2',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                # agent_name should be preserved as-is
                self.assertEqual(call_kwargs['metadata']['agent_name'], 'Quality Check #2')

    def test_save_crew_token_usage_metadata_includes_job_id_and_agent_name(self):
        """Test that metadata includes both job_id and agent_name."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Researcher',
                'agent_name': 'Article Search',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('utils.token_usage.calculate_cost', return_value=0.001):
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                call_kwargs = mock_repo.save.call_args[1]
                metadata = call_kwargs['metadata']
                # Verify both fields exist
                self.assertIn('job_id', metadata)
                self.assertIn('agent_name', metadata)
                self.assertEqual(metadata['job_id'], self.job_id)
                self.assertEqual(metadata['agent_name'], 'Article Search')

    def test_save_crew_token_usage_logs_agent_names_in_usage_data(self):
        """Test that agent usage logging includes agent role."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'News Researcher',
                'agent_name': 'Article Search',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            },
            {
                'agent_role': 'Article Writer',
                'agent_name': None,
                'model': 'gpt-4',
                'prompt_tokens': 500,
                'completion_tokens': 250,
                'total_tokens': 750
            }
        ]

        with patch('utils.token_usage.calculate_cost') as mock_calculate:
            mock_calculate.side_effect = [0.001, 0.01]
            with patch('utils.token_usage.logger') as mock_logger:
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    self.user_id,
                    self.article_id,
                    self.job_id,
                    repo=mock_repo
                )

                # Check that logger captured the agent roles in usageData
                first_info_call = mock_logger.info.call_args_list[0]
                extra = first_info_call[1]['extra']
                self.assertIn('usageData', extra)
                usage_data = extra['usageData']
                self.assertEqual(len(usage_data), 2)
                # First agent should have role info
                self.assertEqual(usage_data[0]['role'], 'News Researcher')
                self.assertEqual(usage_data[1]['role'], 'Article Writer')


class TestCalculateCostIntegration(unittest.TestCase):
    """Integration tests between calculate_cost and save_crew_token_usage."""

    def test_calculate_cost_integration_with_save_crew(self):
        """Test full flow: calculate_cost called within save_crew_token_usage."""
        mock_result = Mock()
        mock_result.get_agent_usage.return_value = [
            {
                'agent_role': 'Integration Test Agent',
                'agent_name': 'Integration Test',
                'model': 'gpt-4.1-mini',
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        ]

        with patch('litellm.cost_per_token') as mock_cost:
            mock_cost.return_value = (0.001, 0.002)
            with patch('utils.token_usage.logger'):
                mock_repo = MagicMock()
                save_crew_token_usage(
                    mock_result,
                    "user-123",
                    "article-456",
                    "job-789",
                    repo=mock_repo
                )

                # Verify cost was calculated correctly
                call_kwargs = mock_repo.save.call_args[1]
                self.assertEqual(call_kwargs['estimated_cost'], 0.003)


if __name__ == '__main__':
    unittest.main()
