"""Tests for DictionaryService with focus on new/changed logic.

Tests cover:
1. _select_best_sense: Uses call_llm_with_tracking, returns tuple, regex parsing
2. _fallback_full_llm: Returns DEFAULT_DEFINITION on JSON parse failure
3. Prompt functions: build_reduced_word_definition_prompt dispatch
4. Token stats accumulation in hybrid lookup
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import re

from services.dictionary_service import (
    DictionaryService,
    LookupRequest,
    LookupResult,
    DEFAULT_DEFINITION,
    REDUCED_PROMPT_MAX_TOKENS,
    FULL_PROMPT_MAX_TOKENS,
)
from utils.dictionary_api import DictionaryAPIResult
from utils.llm import TokenUsageStats
from utils.prompts import (
    build_reduced_word_definition_prompt,
    build_reduced_prompt_de,
    build_reduced_prompt_en,
)


class TestSelectBestSense(unittest.IsolatedAsyncioTestCase):
    """Test _select_best_sense method with new LLM tracking and regex parsing."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = DictionaryService()

    async def test_single_sense_returns_without_llm_call(self):
        """Test single sense returns first sense without LLM call."""
        senses = [{"definition": "only sense"}]

        result, stats = await self.service._select_best_sense(
            "Test sentence", senses
        )

        self.assertEqual(result, senses[0])
        self.assertIsNone(stats)

    async def test_empty_senses_returns_default_definition(self):
        """Test empty senses list returns default definition."""
        senses = []

        result, stats = await self.service._select_best_sense(
            "Test sentence", senses
        )

        self.assertEqual(result, {"definition": DEFAULT_DEFINITION})
        self.assertIsNone(stats)

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_multiple_senses_calls_llm_and_returns_stats(self, mock_llm):
        """Test multiple senses triggers LLM call and returns token stats."""
        senses = [
            {"definition": "first sense"},
            {"definition": "second sense"},
            {"definition": "third sense"},
        ]
        stats = TokenUsageStats(
            model="test-model",
            prompt_tokens=50,
            completion_tokens=10,
            total_tokens=60,
            estimated_cost=0.001,
        )
        mock_llm.return_value = ("1", stats)

        result, returned_stats = await self.service._select_best_sense(
            "Test sentence", senses
        )

        self.assertEqual(result, senses[0])
        self.assertEqual(returned_stats, stats)
        mock_llm.assert_called_once()

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_regex_parsing_plain_digit(self, mock_llm):
        """Test regex parsing handles plain digit '1'."""
        senses = [
            {"definition": "first"},
            {"definition": "second"},
        ]
        stats = TokenUsageStats(
            model="test", prompt_tokens=1, completion_tokens=1,
            total_tokens=2, estimated_cost=0.0
        )
        mock_llm.return_value = ("1", stats)

        result, _ = await self.service._select_best_sense(
            "Sentence", senses
        )

        self.assertEqual(result, senses[0])

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_regex_parsing_digit_with_dot(self, mock_llm):
        """Test regex parsing handles '1.' format."""
        senses = [
            {"definition": "first"},
            {"definition": "second"},
        ]
        stats = TokenUsageStats(
            model="test", prompt_tokens=1, completion_tokens=1,
            total_tokens=2, estimated_cost=0.0
        )
        mock_llm.return_value = ("1.", stats)

        result, _ = await self.service._select_best_sense(
            "Sentence", senses
        )

        self.assertEqual(result, senses[0])

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_regex_parsing_answer_prefix(self, mock_llm):
        """Test regex parsing handles 'Answer: 1' format."""
        senses = [
            {"definition": "first"},
            {"definition": "second"},
            {"definition": "third"},
        ]
        stats = TokenUsageStats(
            model="test", prompt_tokens=1, completion_tokens=1,
            total_tokens=2, estimated_cost=0.0
        )
        mock_llm.return_value = ("Answer: 2", stats)

        result, _ = await self.service._select_best_sense(
            "Sentence", senses
        )

        self.assertEqual(result, senses[1])

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_regex_parsing_no_match_returns_first(self, mock_llm):
        """Test regex parsing when no digit found returns first sense."""
        senses = [
            {"definition": "first"},
            {"definition": "second"},
        ]
        stats = TokenUsageStats(
            model="test", prompt_tokens=1, completion_tokens=1,
            total_tokens=2, estimated_cost=0.0
        )
        mock_llm.return_value = ("No valid response", stats)

        result, _ = await self.service._select_best_sense(
            "Sentence", senses
        )

        self.assertEqual(result, senses[0])

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_regex_parsing_out_of_bounds_returns_first(self, mock_llm):
        """Test regex parsing when digit is out of bounds returns first."""
        senses = [
            {"definition": "first"},
            {"definition": "second"},
        ]
        stats = TokenUsageStats(
            model="test", prompt_tokens=1, completion_tokens=1,
            total_tokens=2, estimated_cost=0.0
        )
        mock_llm.return_value = ("99", stats)

        result, _ = await self.service._select_best_sense(
            "Sentence", senses
        )

        self.assertEqual(result, senses[0])

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_regex_parsing_zero_index(self, mock_llm):
        """Test regex parsing with 0 returns first sense (0-indexed internally)."""
        senses = [
            {"definition": "first"},
            {"definition": "second"},
        ]
        stats = TokenUsageStats(
            model="test", prompt_tokens=1, completion_tokens=1,
            total_tokens=2, estimated_cost=0.0
        )
        mock_llm.return_value = ("0", stats)

        result, _ = await self.service._select_best_sense(
            "Sentence", senses
        )

        # 0 - 1 = -1, which is out of bounds, should return first
        self.assertEqual(result, senses[0])

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_max_tokens_parameter(self, mock_llm):
        """Test _select_best_sense passes max_tokens=10 to LLM."""
        senses = [
            {"definition": "first"},
            {"definition": "second"},
        ]
        mock_llm.return_value = (
            "1",
            TokenUsageStats(
                model="test", prompt_tokens=1, completion_tokens=1,
                total_tokens=2, estimated_cost=0.0
            )
        )

        await self.service._select_best_sense("Sentence", senses)

        # Verify call_llm_with_tracking was called with max_tokens=10
        mock_llm.assert_called_once()
        call_kwargs = mock_llm.call_args[1]
        self.assertEqual(call_kwargs['max_tokens'], 10)

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_temperature_zero_parameter(self, mock_llm):
        """Test _select_best_sense passes temperature=0."""
        senses = [
            {"definition": "first"},
            {"definition": "second"},
        ]
        mock_llm.return_value = (
            "1",
            TokenUsageStats(
                model="test", prompt_tokens=1, completion_tokens=1,
                total_tokens=2, estimated_cost=0.0
            )
        )

        await self.service._select_best_sense("Sentence", senses)

        call_kwargs = mock_llm.call_args[1]
        self.assertEqual(call_kwargs['temperature'], 0)

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_timeout_parameter(self, mock_llm):
        """Test _select_best_sense passes timeout=15."""
        senses = [
            {"definition": "first"},
            {"definition": "second"},
        ]
        mock_llm.return_value = (
            "1",
            TokenUsageStats(
                model="test", prompt_tokens=1, completion_tokens=1,
                total_tokens=2, estimated_cost=0.0
            )
        )

        await self.service._select_best_sense("Sentence", senses)

        call_kwargs = mock_llm.call_args[1]
        self.assertEqual(call_kwargs['timeout'], 15)

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_exception_during_llm_call_returns_first_sense(self, mock_llm):
        """Test exception during LLM call gracefully returns first sense."""
        senses = [
            {"definition": "first"},
            {"definition": "second"},
        ]
        mock_llm.side_effect = Exception("LLM error")

        result, stats = await self.service._select_best_sense(
            "Sentence", senses
        )

        self.assertEqual(result, senses[0])
        self.assertIsNone(stats)

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_limits_to_six_senses(self, mock_llm):
        """Test that only 6 senses are sent to LLM."""
        senses = [
            {"definition": f"sense {i+1}"}
            for i in range(10)
        ]
        mock_llm.return_value = (
            "2",
            TokenUsageStats(
                model="test", prompt_tokens=1, completion_tokens=1,
                total_tokens=2, estimated_cost=0.0
            )
        )

        await self.service._select_best_sense("Sentence", senses)

        # Verify only 6 senses in prompt
        messages = mock_llm.call_args.kwargs['messages']
        prompt_text = messages[0]['content']
        # Count number of "1.", "2.", etc. in prompt
        sense_count = len(re.findall(r'^\d+\.', prompt_text, re.MULTILINE))
        self.assertEqual(sense_count, 6)

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_selected_sense_from_multiple_options(self, mock_llm):
        """Test selecting correct sense from multiple options."""
        senses = [
            {"definition": "sense 1"},
            {"definition": "sense 2"},
            {"definition": "sense 3"},
        ]
        mock_llm.return_value = (
            "3",
            TokenUsageStats(
                model="test", prompt_tokens=1, completion_tokens=1,
                total_tokens=2, estimated_cost=0.0
            )
        )

        result, _ = await self.service._select_best_sense(
            "Sentence", senses
        )

        self.assertEqual(result, senses[2])


class TestFallbackFullLLM(unittest.IsolatedAsyncioTestCase):
    """Test _fallback_full_llm with new behavior on JSON parse failure."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = DictionaryService()

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_returns_parsed_json_on_success(self, mock_llm):
        """Test successful parsing returns LookupResult with parsed fields."""
        stats = TokenUsageStats(
            model="test", prompt_tokens=100, completion_tokens=50,
            total_tokens=150, estimated_cost=0.005
        )
        llm_response = '{"lemma": "test", "definition": "test definition", "level": "A1"}'
        mock_llm.return_value = (llm_response, stats)

        request = LookupRequest(
            word="test",
            sentence="This is a test sentence",
            language="English"
        )

        result = await self.service._fallback_full_llm(request)

        self.assertEqual(result.lemma, "test")
        self.assertEqual(result.definition, "test definition")
        self.assertEqual(result.level, "A1")
        self.assertEqual(result.source, "llm")

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_returns_default_definition_on_parse_failure(self, mock_llm):
        """Test JSON parse failure returns DEFAULT_DEFINITION instead of raw content."""
        stats = TokenUsageStats(
            model="test", prompt_tokens=100, completion_tokens=50,
            total_tokens=150, estimated_cost=0.005
        )
        # Invalid JSON response
        mock_llm.return_value = ("This is not JSON", stats)

        request = LookupRequest(
            word="test",
            sentence="This is a test sentence",
            language="English"
        )

        result = await self.service._fallback_full_llm(request)

        # Should return DEFAULT_DEFINITION, not raw content
        self.assertEqual(result.definition, DEFAULT_DEFINITION)
        self.assertEqual(result.lemma, "test")

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_stores_token_stats(self, mock_llm):
        """Test that token stats are stored in _last_stats."""
        stats = TokenUsageStats(
            model="test-model", prompt_tokens=100, completion_tokens=50,
            total_tokens=150, estimated_cost=0.005
        )
        llm_response = '{"lemma": "test", "definition": "def"}'
        mock_llm.return_value = (llm_response, stats)

        request = LookupRequest(
            word="test",
            sentence="Test sentence",
            language="English"
        )

        await self.service._fallback_full_llm(request)

        self.assertEqual(self.service._last_stats, stats)

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_passes_full_prompt_max_tokens(self, mock_llm):
        """Test that FULL_PROMPT_MAX_TOKENS is passed to LLM call."""
        stats = TokenUsageStats(
            model="test", prompt_tokens=1, completion_tokens=1,
            total_tokens=2, estimated_cost=0.0
        )
        mock_llm.return_value = ('{}', stats)

        request = LookupRequest(
            word="test",
            sentence="Test",
            language="English"
        )

        await self.service._fallback_full_llm(request)

        call_kwargs = mock_llm.call_args[1]
        self.assertEqual(call_kwargs['max_tokens'], FULL_PROMPT_MAX_TOKENS)

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_passes_temperature_zero(self, mock_llm):
        """Test that temperature=0 is passed to LLM call."""
        stats = TokenUsageStats(
            model="test", prompt_tokens=1, completion_tokens=1,
            total_tokens=2, estimated_cost=0.0
        )
        mock_llm.return_value = ('{}', stats)

        request = LookupRequest(
            word="test",
            sentence="Test",
            language="English"
        )

        await self.service._fallback_full_llm(request)

        call_kwargs = mock_llm.call_args[1]
        self.assertEqual(call_kwargs['temperature'], 0)

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_with_all_fields_from_json(self, mock_llm):
        """Test with complete JSON response from LLM."""
        stats = TokenUsageStats(
            model="test", prompt_tokens=100, completion_tokens=50,
            total_tokens=150, estimated_cost=0.005
        )
        llm_response = '''{
            "lemma": "fahren",
            "definition": "to drive",
            "related_words": ["fährt"],
            "pos": "verb",
            "gender": null,
            "level": "B1",
            "conjugations": {"present": "fährt", "past": "fuhr"}
        }'''
        mock_llm.return_value = (llm_response, stats)

        request = LookupRequest(
            word="fährt",
            sentence="Er fährt nach Berlin",
            language="German"
        )

        result = await self.service._fallback_full_llm(request)

        self.assertEqual(result.lemma, "fahren")
        self.assertEqual(result.definition, "to drive")
        self.assertEqual(result.pos, "verb")
        self.assertEqual(result.level, "B1")
        self.assertEqual(result.conjugations, {"present": "fährt", "past": "fuhr"})

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_partial_json_still_uses_default_for_missing_fields(self, mock_llm):
        """Test that DEFAULT_DEFINITION is used when definition field missing."""
        stats = TokenUsageStats(
            model="test", prompt_tokens=100, completion_tokens=50,
            total_tokens=150, estimated_cost=0.005
        )
        llm_response = '{"lemma": "test", "level": "A1"}'  # no definition field
        mock_llm.return_value = (llm_response, stats)

        request = LookupRequest(
            word="test",
            sentence="Test",
            language="English"
        )

        result = await self.service._fallback_full_llm(request)

        self.assertEqual(result.definition, DEFAULT_DEFINITION)
        self.assertEqual(result.lemma, "test")


class TestPerformHybridLookupTokenStats(unittest.IsolatedAsyncioTestCase):
    """Test token stats accumulation in _perform_hybrid_lookup."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = DictionaryService()

    @patch('services.dictionary_service.fetch_from_free_dictionary_api')
    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_accumulates_reduced_and_sense_stats(self, mock_llm, mock_api):
        """Test that sense selection stats are added to reduced prompt stats."""
        # Setup reduced prompt stats
        reduced_stats = TokenUsageStats(
            model="test", prompt_tokens=50, completion_tokens=25,
            total_tokens=75, estimated_cost=0.001
        )
        # Setup sense selection stats
        sense_stats = TokenUsageStats(
            model="test", prompt_tokens=100, completion_tokens=10,
            total_tokens=110, estimated_cost=0.002
        )

        # Mock reduced LLM call
        mock_llm.return_value = (
            '{"lemma": "test", "level": "A1", "related_words": []}',
            reduced_stats
        )

        # Mock API response with multiple senses
        dict_result = DictionaryAPIResult(
            pos="noun",
            all_senses=[
                {"definition": "sense 1"},
                {"definition": "sense 2"},
            ]
        )
        mock_api.return_value = dict_result

        # Mock sense selection LLM call
        with patch.object(
            self.service, '_select_best_sense',
            return_value=({"definition": "sense 1"}, sense_stats)
        ):
            request = LookupRequest(
                word="test",
                sentence="Test sentence",
                language="English"
            )

            result = await self.service._perform_hybrid_lookup(request)

        # Verify stats were accumulated
        accumulated_stats = self.service._last_stats
        self.assertIsNotNone(accumulated_stats)
        self.assertEqual(accumulated_stats.prompt_tokens, 50 + 100)
        self.assertEqual(accumulated_stats.completion_tokens, 25 + 10)
        self.assertEqual(accumulated_stats.total_tokens, 75 + 110)
        self.assertAlmostEqual(accumulated_stats.estimated_cost, 0.003, places=5)

    @patch('services.dictionary_service.fetch_from_free_dictionary_api')
    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_no_sense_stats_doesnt_double_count(self, mock_llm, mock_api):
        """Test that when sense_stats is None, only reduced stats are used."""
        reduced_stats = TokenUsageStats(
            model="test", prompt_tokens=50, completion_tokens=25,
            total_tokens=75, estimated_cost=0.001
        )

        mock_llm.return_value = (
            '{"lemma": "test", "level": "A1", "related_words": []}',
            reduced_stats
        )

        dict_result = DictionaryAPIResult(
            pos="noun",
            all_senses=[{"definition": "only sense"}]  # Single sense
        )
        mock_api.return_value = dict_result

        # Single sense returns None for stats
        with patch.object(
            self.service, '_select_best_sense',
            return_value=({"definition": "only sense"}, None)
        ):
            request = LookupRequest(
                word="test",
                sentence="Test sentence",
                language="English"
            )

            await self.service._perform_hybrid_lookup(request)

        accumulated_stats = self.service._last_stats
        self.assertIsNotNone(accumulated_stats)
        self.assertEqual(accumulated_stats.prompt_tokens, 50)
        self.assertEqual(accumulated_stats.completion_tokens, 25)
        self.assertEqual(accumulated_stats.total_tokens, 75)

    @patch('services.dictionary_service.fetch_from_free_dictionary_api')
    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_preserves_model_and_provider_from_first_call(self, mock_llm, mock_api):
        """Test that accumulated stats preserve model and provider from reduced call."""
        reduced_stats = TokenUsageStats(
            model="gpt-4.1-mini",
            prompt_tokens=50,
            completion_tokens=25,
            total_tokens=75,
            estimated_cost=0.001,
            provider="openai"
        )
        sense_stats = TokenUsageStats(
            model="different-model",  # Should be ignored
            prompt_tokens=100,
            completion_tokens=10,
            total_tokens=110,
            estimated_cost=0.002,
            provider="anthropic"  # Should be ignored
        )

        mock_llm.return_value = (
            '{"lemma": "test", "level": "A1", "related_words": []}',
            reduced_stats
        )

        dict_result = DictionaryAPIResult(
            pos="noun",
            all_senses=[
                {"definition": "sense 1"},
                {"definition": "sense 2"},
            ]
        )
        mock_api.return_value = dict_result

        with patch.object(
            self.service, '_select_best_sense',
            return_value=({"definition": "sense 1"}, sense_stats)
        ):
            request = LookupRequest(
                word="test",
                sentence="Test sentence",
                language="English"
            )

            await self.service._perform_hybrid_lookup(request)

        accumulated_stats = self.service._last_stats
        # Model and provider should come from first (reduced) call
        self.assertEqual(accumulated_stats.model, "gpt-4.1-mini")
        self.assertEqual(accumulated_stats.provider, "openai")


class TestBuildReducedWordDefinitionPrompt(unittest.TestCase):
    """Test build_reduced_word_definition_prompt dispatcher."""

    def test_english_language_dispatch(self):
        """Test English language dispatches to build_reduced_prompt_en."""
        prompt = build_reduced_word_definition_prompt(
            language="English",
            sentence="She gave up smoking",
            word="gave"
        )

        # Should contain English-specific content
        self.assertIn("phrasal verb", prompt.lower())
        self.assertIn("gave", prompt)
        self.assertIn("smoking", prompt)

    def test_german_language_dispatch(self):
        """Test German language dispatches to build_reduced_prompt_de."""
        prompt = build_reduced_word_definition_prompt(
            language="German",
            sentence="Er singt unter der Dusche",
            word="singt"
        )

        # Should contain German-specific content
        self.assertIn("infinitive", prompt.lower())
        self.assertIn("singt", prompt)

    def test_unsupported_language_returns_generic_prompt(self):
        """Test unsupported language returns generic prompt."""
        prompt = build_reduced_word_definition_prompt(
            language="French",
            sentence="Il chante dans la douche",
            word="chante"
        )

        # Should return generic prompt
        self.assertIn("analyzing a French sentence", prompt)
        self.assertIn("chante", prompt)

    def test_english_returns_json_instruction(self):
        """Test English prompt includes JSON instruction."""
        prompt = build_reduced_word_definition_prompt(
            language="English",
            sentence="Test",
            word="test"
        )

        self.assertIn("JSON", prompt)
        self.assertIn("lemma", prompt)
        self.assertIn("related_words", prompt)
        self.assertIn("level", prompt)

    def test_german_returns_json_instruction(self):
        """Test German prompt includes JSON instruction."""
        prompt = build_reduced_word_definition_prompt(
            language="German",
            sentence="Test",
            word="test"
        )

        self.assertIn("JSON", prompt)
        self.assertIn("lemma", prompt)
        self.assertIn("related_words", prompt)
        self.assertIn("level", prompt)

    def test_language_case_sensitive(self):
        """Test that language parameter is case-sensitive."""
        # "english" (lowercase) should not match "English"
        prompt = build_reduced_word_definition_prompt(
            language="english",
            sentence="Test",
            word="test"
        )

        # Should be generic, not English-specific
        self.assertIn("english sentence", prompt)

    def test_prompt_contains_sentence_and_word(self):
        """Test that prompt contains the provided sentence and word."""
        sentence = "The quick brown fox jumps"
        word = "fox"

        prompt = build_reduced_word_definition_prompt(
            language="English",
            sentence=sentence,
            word=word
        )

        self.assertIn(sentence, prompt)
        self.assertIn(word, prompt)

    def test_english_specific_examples(self):
        """Test English prompt includes phrasal verb examples."""
        prompt = build_reduced_word_definition_prompt(
            language="English",
            sentence="She gave up",
            word="gave"
        )

        # Check for phrasal verb examples in English
        self.assertIn("give up", prompt)

    def test_german_specific_examples(self):
        """Test German prompt includes separable verb examples."""
        prompt = build_reduced_word_definition_prompt(
            language="German",
            sentence="Er macht zu",
            word="macht"
        )

        # Check for German-specific separable verb content
        self.assertIn("zumachen", prompt)


class TestCallLLMReducedIntegration(unittest.IsolatedAsyncioTestCase):
    """Test _call_llm_reduced integration with prompts and LLM."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = DictionaryService()

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_calls_build_reduced_word_definition_prompt(self, mock_llm):
        """Test that _call_llm_reduced uses build_reduced_word_definition_prompt."""
        stats = TokenUsageStats(
            model="test", prompt_tokens=1, completion_tokens=1,
            total_tokens=2, estimated_cost=0.0
        )
        mock_llm.return_value = ('{"lemma": "test"}', stats)

        request = LookupRequest(
            word="test",
            sentence="Test sentence",
            language="English"
        )

        await self.service._call_llm_reduced(request)

        # Verify the prompt contains English content
        messages = mock_llm.call_args.kwargs['messages']
        prompt = messages[0]['content']
        self.assertIn("Test sentence", prompt)
        self.assertIn("test", prompt)

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_passes_reduced_prompt_max_tokens(self, mock_llm):
        """Test that REDUCED_PROMPT_MAX_TOKENS is passed to LLM."""
        stats = TokenUsageStats(
            model="test", prompt_tokens=1, completion_tokens=1,
            total_tokens=2, estimated_cost=0.0
        )
        mock_llm.return_value = ('{"lemma": "test"}', stats)

        request = LookupRequest(
            word="test",
            sentence="Test",
            language="English"
        )

        await self.service._call_llm_reduced(request)

        call_kwargs = mock_llm.call_args[1]
        self.assertEqual(call_kwargs['max_tokens'], REDUCED_PROMPT_MAX_TOKENS)

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_uses_english_prompt_builder(self, mock_llm):
        """Test that English language uses build_reduced_prompt_en."""
        stats = TokenUsageStats(
            model="test", prompt_tokens=1, completion_tokens=1,
            total_tokens=2, estimated_cost=0.0
        )
        mock_llm.return_value = ('{"lemma": "test"}', stats)

        request = LookupRequest(
            word="gave",
            sentence="She gave up",
            language="English"
        )

        await self.service._call_llm_reduced(request)

        prompt = mock_llm.call_args.kwargs['messages'][0]['content']
        # Should have English-specific content
        self.assertIn("gave", prompt)

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_uses_german_prompt_builder(self, mock_llm):
        """Test that German language uses build_reduced_prompt_de."""
        stats = TokenUsageStats(
            model="test", prompt_tokens=1, completion_tokens=1,
            total_tokens=2, estimated_cost=0.0
        )
        mock_llm.return_value = ('{"lemma": "test"}', stats)

        request = LookupRequest(
            word="singt",
            sentence="Er singt",
            language="German"
        )

        await self.service._call_llm_reduced(request)

        prompt = mock_llm.call_args.kwargs['messages'][0]['content']
        # Should have German-specific content
        self.assertIn("singt", prompt)


class TestRegexSearchPatternInSelectBestSense(unittest.IsolatedAsyncioTestCase):
    """Test the specific regex pattern r'\\d+' used in _select_best_sense."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = DictionaryService()
        self.pattern = r"\d+"

    def test_regex_pattern_matches_simple_digit(self):
        """Test regex pattern matches simple digits."""
        text = "1"
        match = re.search(self.pattern, text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(), "1")

    def test_regex_pattern_matches_multidigit(self):
        """Test regex pattern matches multi-digit numbers."""
        text = "123"
        match = re.search(self.pattern, text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(), "123")

    def test_regex_pattern_finds_first_digit(self):
        """Test regex pattern finds first occurrence."""
        text = "Answer: 2 or 3"
        match = re.search(self.pattern, text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(), "2")

    def test_regex_pattern_handles_text_before_digit(self):
        """Test regex pattern handles text before digit."""
        text = "The answer is 5"
        match = re.search(self.pattern, text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(), "5")

    def test_regex_pattern_handles_text_after_digit(self):
        """Test regex pattern handles text after digit."""
        text = "3."
        match = re.search(self.pattern, text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(), "3")

    def test_regex_pattern_no_match(self):
        """Test regex pattern returns None when no digit."""
        text = "no digits here"
        match = re.search(self.pattern, text)
        self.assertIsNone(match)


class TestEdgeCasesAndIntegration(unittest.IsolatedAsyncioTestCase):
    """Test edge cases and integration scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = DictionaryService()

    @patch('services.dictionary_service.fetch_from_free_dictionary_api')
    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_hybrid_lookup_with_none_stats_on_json_parse_error(self, mock_llm, mock_api):
        """Test hybrid lookup handles JSON parse error in reduced prompt."""
        # Reduced call returns invalid JSON
        stats = TokenUsageStats(
            model="test", prompt_tokens=1, completion_tokens=1,
            total_tokens=2, estimated_cost=0.0
        )
        mock_llm.return_value = ("invalid json", stats)

        request = LookupRequest(
            word="test",
            sentence="Test",
            language="English"
        )

        result = await self.service._perform_hybrid_lookup(request)

        # Should return None to trigger fallback
        self.assertIsNone(result)

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_fallback_with_exception_in_llm_call(self, mock_llm):
        """Test fallback gracefully handles LLM exception."""
        mock_llm.side_effect = RuntimeError("LLM service down")

        request = LookupRequest(
            word="test",
            sentence="Test",
            language="English"
        )

        with self.assertRaises(RuntimeError):
            await self.service._fallback_full_llm(request)

    async def test_lookup_request_dataclass_creation(self):
        """Test LookupRequest dataclass creation."""
        request = LookupRequest(
            word="test",
            sentence="This is a test",
            language="English"
        )

        self.assertEqual(request.word, "test")
        self.assertEqual(request.sentence, "This is a test")
        self.assertEqual(request.language, "English")
        self.assertIsNone(request.article_id)

    async def test_lookup_request_with_article_id(self):
        """Test LookupRequest with optional article_id."""
        request = LookupRequest(
            word="test",
            sentence="Test",
            language="English",
            article_id="abc123"
        )

        self.assertEqual(request.article_id, "abc123")

    async def test_lookup_result_source_defaults_to_hybrid(self):
        """Test LookupResult source defaults to 'hybrid'."""
        result = LookupResult(
            lemma="test",
            definition="test definition"
        )

        self.assertEqual(result.source, "hybrid")

    async def test_lookup_result_with_all_fields(self):
        """Test LookupResult with all optional fields."""
        result = LookupResult(
            lemma="test",
            definition="definition",
            related_words=["test"],
            level="A1",
            pos="noun",
            gender="der",
            phonetics="/test/",
            conjugations={"present": "tests"},
            examples=["Example"],
            source="llm"
        )

        self.assertEqual(result.lemma, "test")
        self.assertEqual(result.definition, "definition")
        self.assertEqual(result.level, "A1")
        self.assertEqual(result.source, "llm")


if __name__ == '__main__':
    unittest.main()
