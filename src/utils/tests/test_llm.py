"""Unit tests for LLM API utilities and token usage tracking.

Tests for:
- TokenUsageStats dataclass creation, field access, and to_dict() method
- call_llm_with_tracking() async function with LiteLLM mocking
- get_llm_error_response() error handling for various exception types
- Edge cases: empty messages, zero tokens, provider extraction, timeout handling
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
import litellm

from utils.llm import (
    TokenUsageStats,
    parse_json_from_content,
    call_llm_with_tracking,
    get_llm_error_response,
    _extract_provider_from_model,
)


class TestTokenUsageStats(unittest.TestCase):
    """Test cases for TokenUsageStats dataclass."""

    def test_creation_with_valid_values(self):
        """Test creating TokenUsageStats with valid values."""
        stats = TokenUsageStats(
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost=0.000225,
        )
        self.assertEqual(stats.model, "gpt-4o-mini")
        self.assertEqual(stats.prompt_tokens, 100)
        self.assertEqual(stats.completion_tokens, 50)
        self.assertEqual(stats.total_tokens, 150)
        self.assertAlmostEqual(stats.estimated_cost, 0.000225, places=6)

    def test_creation_with_zero_tokens(self):
        """Test creating TokenUsageStats with zero tokens."""
        stats = TokenUsageStats(
            model="gpt-4o",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            estimated_cost=0.0,
        )
        self.assertEqual(stats.prompt_tokens, 0)
        self.assertEqual(stats.completion_tokens, 0)
        self.assertEqual(stats.total_tokens, 0)
        self.assertEqual(stats.estimated_cost, 0.0)

    def test_creation_with_large_token_values(self):
        """Test creating TokenUsageStats with large token values."""
        stats = TokenUsageStats(
            model="gpt-4-turbo",
            prompt_tokens=100000,
            completion_tokens=50000,
            total_tokens=150000,
            estimated_cost=2.5,
        )
        self.assertEqual(stats.prompt_tokens, 100000)
        self.assertEqual(stats.completion_tokens, 50000)
        self.assertEqual(stats.total_tokens, 150000)
        self.assertAlmostEqual(stats.estimated_cost, 2.5, places=1)

    def test_all_fields_accessible(self):
        """Test that all fields are accessible as attributes."""
        stats = TokenUsageStats(
            model="test-model",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            estimated_cost=0.001,
        )
        # Verify all fields exist and are accessible
        self.assertTrue(hasattr(stats, "model"))
        self.assertTrue(hasattr(stats, "prompt_tokens"))
        self.assertTrue(hasattr(stats, "completion_tokens"))
        self.assertTrue(hasattr(stats, "total_tokens"))
        self.assertTrue(hasattr(stats, "estimated_cost"))
        self.assertTrue(hasattr(stats, "provider"))

    def test_dataclass_field_types(self):
        """Test that dataclass fields have correct types."""
        stats = TokenUsageStats(
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost=0.000225,
        )
        self.assertIsInstance(stats.model, str)
        self.assertIsInstance(stats.prompt_tokens, int)
        self.assertIsInstance(stats.completion_tokens, int)
        self.assertIsInstance(stats.total_tokens, int)
        self.assertIsInstance(stats.estimated_cost, float)

    def test_provider_field_default_is_none(self):
        """Test that provider field defaults to None."""
        stats = TokenUsageStats(
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost=0.000225,
        )
        self.assertIsNone(stats.provider)

    def test_provider_field_can_be_set(self):
        """Test that provider field can be explicitly set."""
        stats = TokenUsageStats(
            model="anthropic/claude-3-5-sonnet-20241022",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost=0.001,
            provider="anthropic",
        )
        self.assertEqual(stats.provider, "anthropic")

    def test_to_dict_method(self):
        """Test to_dict() method returns correct dictionary."""
        stats = TokenUsageStats(
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost=0.000225,
            provider="openai",
        )
        result = stats.to_dict()
        expected = {
            "model": "gpt-4o-mini",
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
            "estimated_cost": 0.000225,
            "provider": "openai",
        }
        self.assertEqual(result, expected)

    def test_to_dict_with_none_provider(self):
        """Test to_dict() method with None provider."""
        stats = TokenUsageStats(
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost=0.000225,
        )
        result = stats.to_dict()
        self.assertIsNone(result["provider"])


class TestExtractProviderFromModel(unittest.TestCase):
    """Test cases for _extract_provider_from_model() function."""

    def test_openai_model_without_prefix(self):
        """Test OpenAI models without provider prefix."""
        self.assertEqual(_extract_provider_from_model("gpt-4o-mini"), "openai")
        self.assertEqual(_extract_provider_from_model("gpt-4o"), "openai")
        self.assertEqual(_extract_provider_from_model("gpt-4-turbo"), "openai")

    def test_openai_o1_models(self):
        """Test OpenAI o1/o3 models."""
        self.assertEqual(_extract_provider_from_model("o1-preview"), "openai")
        self.assertEqual(_extract_provider_from_model("o1-mini"), "openai")
        self.assertEqual(_extract_provider_from_model("o3-mini"), "openai")

    def test_anthropic_model_with_prefix(self):
        """Test Anthropic models with provider prefix."""
        self.assertEqual(
            _extract_provider_from_model("anthropic/claude-3-5-sonnet-20241022"),
            "anthropic"
        )

    def test_gemini_model_with_prefix(self):
        """Test Gemini models with provider prefix."""
        self.assertEqual(
            _extract_provider_from_model("gemini/gemini-1.5-flash"),
            "gemini"
        )

    def test_unknown_model_without_prefix(self):
        """Test unknown models without recognizable prefix."""
        self.assertIsNone(_extract_provider_from_model("unknown-model"))


class TestParseJsonFromContent(unittest.TestCase):
    """Test cases for parse_json_from_content() function."""

    def test_parse_plain_json(self):
        """Test parsing plain JSON content."""
        content = '{"key": "value", "number": 42}'
        result = parse_json_from_content(content)
        self.assertEqual(result, {"key": "value", "number": 42})

    def test_parse_json_in_markdown_code_block(self):
        """Test parsing JSON from markdown code block."""
        content = '```json\n{"key": "value"}\n```'
        result = parse_json_from_content(content)
        self.assertEqual(result, {"key": "value"})

    def test_parse_json_in_generic_code_block(self):
        """Test parsing JSON from generic markdown code block."""
        content = '```\n{"key": "value"}\n```'
        result = parse_json_from_content(content)
        self.assertEqual(result, {"key": "value"})

    def test_parse_json_with_surrounding_text(self):
        """Test parsing JSON with surrounding text."""
        content = 'Here is some JSON: {"key": "value"} and more text'
        result = parse_json_from_content(content)
        self.assertEqual(result, {"key": "value"})

    def test_parse_invalid_json_returns_none(self):
        """Test that invalid JSON returns None."""
        content = '{"incomplete": '
        result = parse_json_from_content(content)
        self.assertIsNone(result)

    def test_parse_empty_string_returns_none(self):
        """Test that empty string returns None."""
        result = parse_json_from_content("")
        self.assertIsNone(result)

    def test_parse_no_json_in_content_returns_none(self):
        """Test that content without JSON returns None."""
        result = parse_json_from_content("just some plain text")
        self.assertIsNone(result)

    def test_parse_json_with_nested_objects(self):
        """Test parsing JSON with nested objects."""
        content = '{"outer": {"inner": "value"}}'
        result = parse_json_from_content(content)
        self.assertEqual(result, {"outer": {"inner": "value"}})

    def test_parse_json_with_arrays(self):
        """Test parsing JSON with arrays."""
        content = '{"items": [1, 2, 3]}'
        result = parse_json_from_content(content)
        self.assertEqual(result, {"items": [1, 2, 3]})

    def test_parse_json_with_whitespace_in_markdown(self):
        """Test parsing JSON with extra whitespace in markdown."""
        content = '```json\n  \n  {"key": "value"}  \n  \n```'
        result = parse_json_from_content(content)
        self.assertEqual(result, {"key": "value"})


class TestCallLlmWithTracking(unittest.TestCase):
    """Test cases for call_llm_with_tracking() async function."""

    def test_successful_api_call_returns_content_and_stats(self):
        """Test successful API call returns content and TokenUsageStats."""
        # Create mock response
        mock_message = Mock()
        mock_message.content = "Test response content"

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_usage = Mock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 20
        mock_usage.total_tokens = 30

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        mock_response.id = "chatcmpl-123"

        async def run_test():
            with patch("utils.llm.acompletion", new_callable=AsyncMock) as mock_acompletion:
                with patch("utils.llm.completion_cost", return_value=0.0001):
                    mock_acompletion.return_value = mock_response

                    messages = [{"role": "user", "content": "Hello"}]
                    content, stats = await call_llm_with_tracking(messages)

                    self.assertEqual(content, "Test response content")
                    self.assertIsInstance(stats, TokenUsageStats)
                    self.assertEqual(stats.prompt_tokens, 10)
                    self.assertEqual(stats.completion_tokens, 20)
                    self.assertEqual(stats.total_tokens, 30)

        asyncio.run(run_test())

    def test_empty_messages_list_raises_value_error(self):
        """Test that empty messages list raises ValueError."""

        async def run_test():
            with self.assertRaises(ValueError) as cm:
                await call_llm_with_tracking([])
            self.assertIn("messages", str(cm.exception).lower())

        asyncio.run(run_test())

    def test_timeout_parameter_is_passed_correctly(self):
        """Test that timeout parameter is passed to acompletion."""
        mock_message = Mock()
        mock_message.content = "Response"

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_usage = Mock()
        mock_usage.prompt_tokens = 5
        mock_usage.completion_tokens = 10
        mock_usage.total_tokens = 15

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        mock_response.id = "chatcmpl-456"

        async def run_test():
            with patch("utils.llm.acompletion", new_callable=AsyncMock) as mock_acompletion:
                with patch("utils.llm.completion_cost", return_value=0.0001):
                    mock_acompletion.return_value = mock_response

                    messages = [{"role": "user", "content": "Test"}]
                    custom_timeout = 60.0
                    await call_llm_with_tracking(messages, timeout=custom_timeout)

                    # Verify acompletion was called with correct timeout
                    mock_acompletion.assert_called_once()
                    call_kwargs = mock_acompletion.call_args[1]
                    self.assertEqual(call_kwargs.get("timeout"), custom_timeout)

        asyncio.run(run_test())

    def test_additional_kwargs_passed_to_api(self):
        """Test that additional kwargs are passed to acompletion()."""
        mock_message = Mock()
        mock_message.content = "Response"

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_usage = Mock()
        mock_usage.prompt_tokens = 5
        mock_usage.completion_tokens = 10
        mock_usage.total_tokens = 15

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        mock_response.id = "chatcmpl-789"

        async def run_test():
            with patch("utils.llm.acompletion", new_callable=AsyncMock) as mock_acompletion:
                with patch("utils.llm.completion_cost", return_value=0.0001):
                    mock_acompletion.return_value = mock_response

                    messages = [{"role": "user", "content": "Test"}]
                    await call_llm_with_tracking(
                        messages,
                        model="gpt-4o",
                        max_tokens=200,
                        temperature=0.7,
                    )

                    # Verify create was called with additional kwargs
                    mock_acompletion.assert_called_once()
                    call_kwargs = mock_acompletion.call_args[1]
                    self.assertEqual(call_kwargs.get("model"), "gpt-4o")
                    self.assertEqual(call_kwargs.get("max_tokens"), 200)
                    self.assertEqual(call_kwargs.get("temperature"), 0.7)

        asyncio.run(run_test())

    def test_cost_calculation_uses_litellm_completion_cost(self):
        """Test that estimated cost is calculated using LiteLLM completion_cost."""
        mock_message = Mock()
        mock_message.content = "Response"

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_usage = Mock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        mock_response.id = "chatcmpl-cost"

        expected_cost = 0.000225

        async def run_test():
            with patch("utils.llm.acompletion", new_callable=AsyncMock) as mock_acompletion:
                with patch("utils.llm.completion_cost", return_value=expected_cost) as mock_cost:
                    mock_acompletion.return_value = mock_response

                    messages = [{"role": "user", "content": "Test"}]
                    content, stats = await call_llm_with_tracking(
                        messages, model="gpt-4o-mini"
                    )

                    # Verify completion_cost was called with the response
                    mock_cost.assert_called_once_with(completion_response=mock_response)
                    self.assertEqual(stats.estimated_cost, expected_cost)

        asyncio.run(run_test())

    def test_cost_calculation_fallback_on_error(self):
        """Test that cost falls back to 0.0 when completion_cost raises an error."""
        mock_message = Mock()
        mock_message.content = "Response"

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_usage = Mock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        mock_response.id = "chatcmpl-cost-error"

        async def run_test():
            with patch("utils.llm.acompletion", new_callable=AsyncMock) as mock_acompletion:
                with patch("utils.llm.completion_cost", side_effect=Exception("Unknown model")):
                    mock_acompletion.return_value = mock_response

                    messages = [{"role": "user", "content": "Test"}]
                    content, stats = await call_llm_with_tracking(
                        messages, model="unknown-model"
                    )

                    # Should fall back to 0.0
                    self.assertEqual(stats.estimated_cost, 0.0)

        asyncio.run(run_test())

    def test_no_content_in_response_raises_runtime_error(self):
        """Test that no content in response raises RuntimeError."""
        mock_message = Mock()
        mock_message.content = ""  # Empty content

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_usage = Mock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 0
        mock_usage.total_tokens = 10

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        mock_response.id = "chatcmpl-empty"

        async def run_test():
            with patch("utils.llm.acompletion", new_callable=AsyncMock) as mock_acompletion:
                mock_acompletion.return_value = mock_response

                messages = [{"role": "user", "content": "Test"}]
                with self.assertRaises(RuntimeError) as cm:
                    await call_llm_with_tracking(messages)
                self.assertIn("content", str(cm.exception).lower())

        asyncio.run(run_test())

    def test_no_choices_in_response_raises_runtime_error(self):
        """Test that no choices in response raises RuntimeError."""
        mock_usage = Mock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 0
        mock_usage.total_tokens = 10

        mock_response = Mock()
        mock_response.choices = []  # No choices
        mock_response.usage = mock_usage
        mock_response.id = "chatcmpl-nochoice"

        async def run_test():
            with patch("utils.llm.acompletion", new_callable=AsyncMock) as mock_acompletion:
                mock_acompletion.return_value = mock_response

                messages = [{"role": "user", "content": "Test"}]
                with self.assertRaises(RuntimeError):
                    await call_llm_with_tracking(messages)

        asyncio.run(run_test())

    def test_model_parameter_used_in_request(self):
        """Test that model parameter is used in API request."""
        mock_message = Mock()
        mock_message.content = "Response"

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_usage = Mock()
        mock_usage.prompt_tokens = 5
        mock_usage.completion_tokens = 10
        mock_usage.total_tokens = 15

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        mock_response.id = "chatcmpl-model"

        async def run_test():
            with patch("utils.llm.acompletion", new_callable=AsyncMock) as mock_acompletion:
                with patch("utils.llm.completion_cost", return_value=0.0001):
                    mock_acompletion.return_value = mock_response

                    messages = [{"role": "user", "content": "Test"}]
                    model_name = "gpt-4-turbo"
                    content, stats = await call_llm_with_tracking(
                        messages, model=model_name
                    )

                    # Verify model is passed in acompletion call
                    call_kwargs = mock_acompletion.call_args[1]
                    self.assertEqual(call_kwargs.get("model"), model_name)
                    self.assertEqual(stats.model, model_name)

        asyncio.run(run_test())

    def test_default_model_is_gpt41_mini(self):
        """Test that default model is gpt-4.1-mini when not specified."""
        mock_message = Mock()
        mock_message.content = "Response"

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_usage = Mock()
        mock_usage.prompt_tokens = 5
        mock_usage.completion_tokens = 10
        mock_usage.total_tokens = 15

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        mock_response.id = "chatcmpl-default"

        async def run_test():
            with patch("utils.llm.acompletion", new_callable=AsyncMock) as mock_acompletion:
                with patch("utils.llm.completion_cost", return_value=0.0001):
                    mock_acompletion.return_value = mock_response

                    messages = [{"role": "user", "content": "Test"}]
                    content, stats = await call_llm_with_tracking(messages)

                    # Verify default model is used
                    call_kwargs = mock_acompletion.call_args[1]
                    self.assertEqual(call_kwargs.get("model"), "gpt-4.1-mini")
                    self.assertEqual(stats.model, "gpt-4.1-mini")

        asyncio.run(run_test())

    def test_usage_with_none_values(self):
        """Test handling of None usage values."""
        mock_message = Mock()
        mock_message.content = "Response"

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = None  # No usage data

        async def run_test():
            with patch("utils.llm.acompletion", new_callable=AsyncMock) as mock_acompletion:
                with patch("utils.llm.completion_cost", return_value=0.0):
                    mock_acompletion.return_value = mock_response

                    messages = [{"role": "user", "content": "Test"}]
                    content, stats = await call_llm_with_tracking(messages)

                    # Should default to 0 tokens
                    self.assertEqual(stats.prompt_tokens, 0)
                    self.assertEqual(stats.completion_tokens, 0)
                    self.assertEqual(stats.total_tokens, 0)

        asyncio.run(run_test())

    def test_provider_extracted_for_openai_model(self):
        """Test that provider is correctly extracted for OpenAI models."""
        mock_message = Mock()
        mock_message.content = "Response"

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_usage = Mock()
        mock_usage.prompt_tokens = 5
        mock_usage.completion_tokens = 10
        mock_usage.total_tokens = 15

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        mock_response.id = "chatcmpl-provider"

        async def run_test():
            with patch("utils.llm.acompletion", new_callable=AsyncMock) as mock_acompletion:
                with patch("utils.llm.completion_cost", return_value=0.0001):
                    mock_acompletion.return_value = mock_response

                    messages = [{"role": "user", "content": "Test"}]
                    content, stats = await call_llm_with_tracking(
                        messages, model="gpt-4o-mini"
                    )

                    self.assertEqual(stats.provider, "openai")

        asyncio.run(run_test())

    def test_provider_extracted_for_anthropic_model(self):
        """Test that provider is correctly extracted for Anthropic models."""
        mock_message = Mock()
        mock_message.content = "Response"

        mock_choice = Mock()
        mock_choice.message = mock_message

        mock_usage = Mock()
        mock_usage.prompt_tokens = 5
        mock_usage.completion_tokens = 10
        mock_usage.total_tokens = 15

        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        mock_response.id = "chatcmpl-provider"

        async def run_test():
            with patch("utils.llm.acompletion", new_callable=AsyncMock) as mock_acompletion:
                with patch("utils.llm.completion_cost", return_value=0.0001):
                    mock_acompletion.return_value = mock_response

                    messages = [{"role": "user", "content": "Test"}]
                    content, stats = await call_llm_with_tracking(
                        messages, model="anthropic/claude-3-5-sonnet-20241022"
                    )

                    self.assertEqual(stats.provider, "anthropic")

        asyncio.run(run_test())


class TestGetLlmErrorResponse(unittest.TestCase):
    """Test cases for get_llm_error_response() error handling function."""

    def test_value_error_returns_400_invalid_request(self):
        """Test ValueError returns (400, 'Invalid request: ...')."""
        error = ValueError("messages list cannot be empty")
        status_code, message = get_llm_error_response(error)
        self.assertEqual(status_code, 400)
        self.assertIn("Invalid request", message)

    def test_authentication_error_returns_401(self):
        """Test litellm.AuthenticationError returns (401, 'LLM provider authentication failed')."""
        error = litellm.AuthenticationError(
            "Invalid API key",
            llm_provider="openai",
            model="gpt-4o-mini"
        )
        status_code, message = get_llm_error_response(error)
        self.assertEqual(status_code, 401)
        self.assertEqual(message, "LLM provider authentication failed")

    def test_rate_limit_error_returns_429(self):
        """Test litellm.RateLimitError returns (429, 'LLM provider rate limit exceeded')."""
        error = litellm.RateLimitError(
            "Rate limit exceeded",
            llm_provider="openai",
            model="gpt-4o-mini"
        )
        status_code, message = get_llm_error_response(error)
        self.assertEqual(status_code, 429)
        self.assertEqual(message, "LLM provider rate limit exceeded")

    def test_timeout_error_returns_504(self):
        """Test litellm.Timeout returns (504, 'LLM provider timeout')."""
        error = litellm.Timeout(
            "Request timed out",
            llm_provider="openai",
            model="gpt-4o-mini"
        )
        status_code, message = get_llm_error_response(error)
        self.assertEqual(status_code, 504)
        self.assertEqual(message, "LLM provider timeout")

    def test_service_unavailable_error_returns_503(self):
        """Test litellm.ServiceUnavailableError returns (503, 'LLM provider service unavailable')."""
        error = litellm.ServiceUnavailableError(
            "Service unavailable",
            llm_provider="openai",
            model="gpt-4o-mini"
        )
        status_code, message = get_llm_error_response(error)
        self.assertEqual(status_code, 503)
        self.assertEqual(message, "LLM provider service unavailable")

    def test_api_error_returns_502(self):
        """Test litellm.APIError returns (502, 'LLM provider API error')."""
        error = litellm.APIError(
            status_code=500,
            message="Internal server error",
            llm_provider="openai",
            model="gpt-4o-mini"
        )
        status_code, message = get_llm_error_response(error)
        self.assertEqual(status_code, 502)
        self.assertEqual(message, "LLM provider API error")

    def test_runtime_error_returns_500_with_message(self):
        """Test RuntimeError returns (500, 'LLM provider error: ...')."""
        error_msg = "No content returned from API"
        error = RuntimeError(error_msg)
        status_code, message = get_llm_error_response(error)
        self.assertEqual(status_code, 500)
        self.assertIn("LLM provider error", message)
        self.assertIn(error_msg, message)

    def test_unknown_exception_returns_500_internal_server_error(self):
        """Test unknown exception returns (500, 'Internal server error')."""
        error = Exception("Some unexpected error")
        status_code, message = get_llm_error_response(error)
        self.assertEqual(status_code, 500)
        self.assertEqual(message, "Internal server error")

    def test_error_response_tuple_structure(self):
        """Test that response is always a tuple of (int, str)."""
        errors = [
            ValueError("test"),
            litellm.AuthenticationError("test", llm_provider="openai", model="gpt-4o"),
            litellm.RateLimitError("test", llm_provider="openai", model="gpt-4o"),
            Exception("test"),
        ]
        for error in errors:
            result = get_llm_error_response(error)
            self.assertIsInstance(result, tuple)
            self.assertEqual(len(result), 2)
            self.assertIsInstance(result[0], int)
            self.assertIsInstance(result[1], str)

    def test_error_message_is_always_non_empty(self):
        """Test that error message is never empty."""
        errors = [
            ValueError(""),
            litellm.AuthenticationError("", llm_provider="openai", model="gpt-4o"),
            Exception(""),
        ]
        for error in errors:
            status_code, message = get_llm_error_response(error)
            self.assertGreater(len(message), 0)

    def test_status_code_is_valid_http_code(self):
        """Test that returned status code is a valid HTTP code."""
        errors = [
            ValueError("test"),
            litellm.AuthenticationError("test", llm_provider="openai", model="gpt-4o"),
            litellm.RateLimitError("test", llm_provider="openai", model="gpt-4o"),
            litellm.Timeout("test", llm_provider="openai", model="gpt-4o"),
            litellm.ServiceUnavailableError("test", llm_provider="openai", model="gpt-4o"),
            litellm.APIError(status_code=500, message="test", llm_provider="openai", model="gpt-4o"),
            RuntimeError("test"),
            Exception("test"),
        ]
        valid_codes = {400, 401, 402, 403, 404, 429, 500, 501, 502, 503, 504}
        for error in errors:
            status_code, _ = get_llm_error_response(error)
            self.assertIn(status_code, valid_codes)


if __name__ == "__main__":
    unittest.main()
