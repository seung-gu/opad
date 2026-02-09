"""Tests for DictionaryService with focus on new/changed logic.

Tests cover:
1. _select_best_entry_sense: Uses call_llm_with_tracking, returns tuple, regex parsing
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


class TestSelectBestEntrySense(unittest.IsolatedAsyncioTestCase):
    """Test _select_best_entry_sense method with X.Y.Z format parsing."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = DictionaryService()

    async def test_single_entry_single_sense_skips_llm(self):
        """Test single entry with single sense returns defaults without LLM."""
        entries = [{"partOfSpeech": "noun", "senses": [{"definition": "only sense"}]}]

        ei, si, ssi, stats = await self.service._select_best_entry_sense(
            "Test sentence", "word", entries
        )

        self.assertEqual((ei, si, ssi), (0, 0, -1))
        self.assertIsNone(stats)

    async def test_empty_entries_returns_defaults(self):
        """Test empty entries list returns defaults."""
        ei, si, ssi, stats = await self.service._select_best_entry_sense(
            "Test sentence", "word", []
        )

        self.assertEqual((ei, si, ssi), (0, 0, -1))
        self.assertIsNone(stats)

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_xy_parsing_sense_level(self, mock_llm):
        """Test X.Y parsing selects correct entry and sense."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {"definition": "sense 0"},
                {"definition": "sense 1"},
            ]},
            {"partOfSpeech": "verb", "senses": [
                {"definition": "verb sense 0"},
            ]},
        ]
        stats = TokenUsageStats(
            model="test", prompt_tokens=50, completion_tokens=5,
            total_tokens=55, estimated_cost=0.001,
        )
        mock_llm.return_value = ("0.1", stats)

        ei, si, ssi, returned_stats = await self.service._select_best_entry_sense(
            "Sentence", "word", entries
        )

        self.assertEqual((ei, si, ssi), (0, 1, -1))
        self.assertEqual(returned_stats, stats)
        mock_llm.assert_called_once()

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_xyz_parsing_subsense_level(self, mock_llm):
        """Test X.Y.Z parsing selects correct subsense."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {
                    "definition": "main sense",
                    "subsenses": [
                        {"definition": "subsense 0"},
                        {"definition": "subsense 1"},
                    ]
                },
            ]},
        ]
        stats = TokenUsageStats(
            model="test", prompt_tokens=50, completion_tokens=5,
            total_tokens=55, estimated_cost=0.001,
        )
        mock_llm.return_value = ("0.0.1", stats)

        ei, si, ssi, _ = await self.service._select_best_entry_sense(
            "Sentence", "word", entries
        )

        self.assertEqual((ei, si, ssi), (0, 0, 1))

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_clamping_out_of_bounds_entry(self, mock_llm):
        """Test out-of-bounds entry index is clamped."""
        entries = [
            {"partOfSpeech": "noun", "senses": [{"definition": "only"}]},
        ]
        stats = TokenUsageStats(
            model="test", prompt_tokens=1, completion_tokens=1,
            total_tokens=2, estimated_cost=0.0,
        )
        # Entry index 5 should clamp to 0 (only 1 entry)
        mock_llm.return_value = ("5.0", stats)

        ei, si, ssi, _ = await self.service._select_best_entry_sense(
            "Sentence", "word", entries
        )

        self.assertEqual(ei, 0)

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_clamping_out_of_bounds_sense(self, mock_llm):
        """Test out-of-bounds sense index is clamped."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {"definition": "sense 0"},
                {"definition": "sense 1"},
            ]},
        ]
        stats = TokenUsageStats(
            model="test", prompt_tokens=1, completion_tokens=1,
            total_tokens=2, estimated_cost=0.0,
        )
        mock_llm.return_value = ("0.99", stats)

        ei, si, ssi, _ = await self.service._select_best_entry_sense(
            "Sentence", "word", entries
        )

        self.assertEqual(si, 1)  # clamped to max index

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_clamping_out_of_bounds_subsense(self, mock_llm):
        """Test out-of-bounds subsense index is clamped."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {
                    "definition": "main",
                    "subsenses": [{"definition": "sub 0"}]
                },
            ]},
        ]
        stats = TokenUsageStats(
            model="test", prompt_tokens=1, completion_tokens=1,
            total_tokens=2, estimated_cost=0.0,
        )
        mock_llm.return_value = ("0.0.5", stats)

        ei, si, ssi, _ = await self.service._select_best_entry_sense(
            "Sentence", "word", entries
        )

        self.assertEqual(ssi, 0)  # clamped to max index

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_prompt_contains_all_entries_no_truncation(self, mock_llm):
        """Test prompt includes all entries/senses without truncation."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {"definition": f"noun sense {i}"} for i in range(8)
            ]},
            {"partOfSpeech": "verb", "senses": [
                {"definition": f"verb sense {i}"} for i in range(4)
            ]},
        ]
        stats = TokenUsageStats(
            model="test", prompt_tokens=1, completion_tokens=1,
            total_tokens=2, estimated_cost=0.0,
        )
        mock_llm.return_value = ("0.0", stats)

        await self.service._select_best_entry_sense("Sentence", "word", entries)

        prompt_text = mock_llm.call_args.kwargs['messages'][0]['content']
        # All 12 senses should be present (no [:6] truncation)
        self.assertIn("0.7", prompt_text)  # 8th noun sense
        self.assertIn("1.3", prompt_text)  # 4th verb sense
        self.assertIn("entries[0]", prompt_text)
        self.assertIn("entries[1]", prompt_text)

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_exception_returns_defaults(self, mock_llm):
        """Test exception during LLM call returns safe defaults."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {"definition": "first"},
                {"definition": "second"},
            ]},
        ]
        mock_llm.side_effect = Exception("LLM error")

        ei, si, ssi, stats = await self.service._select_best_entry_sense(
            "Sentence", "word", entries
        )

        self.assertEqual((ei, si, ssi), (0, 0, -1))
        self.assertIsNone(stats)

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_no_xy_match_returns_defaults(self, mock_llm):
        """Test LLM response without X.Y format returns defaults."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {"definition": "first"},
                {"definition": "second"},
            ]},
        ]
        stats = TokenUsageStats(
            model="test", prompt_tokens=1, completion_tokens=1,
            total_tokens=2, estimated_cost=0.0,
        )
        mock_llm.return_value = ("No valid response", stats)

        ei, si, ssi, _ = await self.service._select_best_entry_sense(
            "Sentence", "word", entries
        )

        self.assertEqual((ei, si, ssi), (0, 0, -1))

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_selects_second_entry(self, mock_llm):
        """Test selecting entry from second entry (verb)."""
        entries = [
            {"partOfSpeech": "noun", "senses": [{"definition": "a thing"}]},
            {"partOfSpeech": "verb", "senses": [{"definition": "to do something"}]},
        ]
        stats = TokenUsageStats(
            model="test", prompt_tokens=1, completion_tokens=1,
            total_tokens=2, estimated_cost=0.0,
        )
        mock_llm.return_value = ("1.0", stats)

        ei, si, ssi, _ = await self.service._select_best_entry_sense(
            "Sentence", "word", entries
        )

        self.assertEqual((ei, si, ssi), (1, 0, -1))

    @patch('services.dictionary_service.call_llm_with_tracking')
    async def test_max_tokens_parameter(self, mock_llm):
        """Test passes max_tokens=10 to LLM."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {"definition": "first"},
                {"definition": "second"},
            ]},
        ]
        mock_llm.return_value = (
            "0.0",
            TokenUsageStats(
                model="test", prompt_tokens=1, completion_tokens=1,
                total_tokens=2, estimated_cost=0.0
            )
        )

        await self.service._select_best_entry_sense("Sentence", "word", entries)

        call_kwargs = mock_llm.call_args[1]
        self.assertEqual(call_kwargs['max_tokens'], 10)
        self.assertEqual(call_kwargs['temperature'], 0)
        self.assertEqual(call_kwargs['timeout'], 15)


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

        # Mock API response with multiple entries
        dict_result = DictionaryAPIResult(
            all_entries=[
                {"partOfSpeech": "noun", "senses": [
                    {"definition": "sense 1"},
                    {"definition": "sense 2"},
                ]}
            ]
        )
        mock_api.return_value = dict_result

        # Mock entry+sense selection
        with patch.object(
            self.service, '_select_best_entry_sense',
            return_value=(0, 0, -1, sense_stats)
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
            all_entries=[
                {"partOfSpeech": "noun", "senses": [{"definition": "only sense"}]}
            ]
        )
        mock_api.return_value = dict_result

        # Single entry+sense returns None for stats
        with patch.object(
            self.service, '_select_best_entry_sense',
            return_value=(0, 0, -1, None)
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
            all_entries=[
                {"partOfSpeech": "noun", "senses": [
                    {"definition": "sense 1"},
                    {"definition": "sense 2"},
                ]}
            ]
        )
        mock_api.return_value = dict_result

        with patch.object(
            self.service, '_select_best_entry_sense',
            return_value=(0, 0, -1, sense_stats)
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


class TestRegexSearchPatternInSelectBestEntrySense(unittest.IsolatedAsyncioTestCase):
    """Test the X.Y.Z regex pattern used in _select_best_entry_sense."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = DictionaryService()
        self.pattern = r"(\d+)\.(\d+)(?:\.(\d+))?"

    def test_regex_matches_xy_format(self):
        """Test regex matches X.Y format."""
        match = re.search(self.pattern, "0.1")
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "0")
        self.assertEqual(match.group(2), "1")
        self.assertIsNone(match.group(3))

    def test_regex_matches_xyz_format(self):
        """Test regex matches X.Y.Z format."""
        match = re.search(self.pattern, "1.2.3")
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "1")
        self.assertEqual(match.group(2), "2")
        self.assertEqual(match.group(3), "3")

    def test_regex_finds_first_match_in_text(self):
        """Test regex finds first X.Y in surrounding text."""
        match = re.search(self.pattern, "Answer: 0.2")
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "0")
        self.assertEqual(match.group(2), "2")

    def test_regex_no_match_plain_digit(self):
        """Test regex does not match plain digit without dot."""
        match = re.search(self.pattern, "5")
        self.assertIsNone(match)

    def test_regex_no_match_no_digits(self):
        """Test regex returns None when no digits."""
        match = re.search(self.pattern, "no digits here")
        self.assertIsNone(match)

    def test_regex_multidigit_indices(self):
        """Test regex handles multi-digit indices."""
        match = re.search(self.pattern, "10.15")
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "10")
        self.assertEqual(match.group(2), "15")


class TestGetDefinitionFromSelection(unittest.TestCase):
    """Test _get_definition_from_selection static method with edge cases."""

    def test_valid_sense_index_returns_definition_and_sense(self):
        """Test valid sense index returns definition and sense dict."""
        entry = {
            "senses": [
                {"definition": "First sense definition"},
                {"definition": "Second sense definition"},
            ]
        }

        definition, sense = DictionaryService._get_definition_from_selection(entry, 0, -1)

        self.assertEqual(definition, "First sense definition")
        self.assertIsNotNone(sense)
        self.assertEqual(sense.get("definition"), "First sense definition")

    def test_valid_second_sense_index(self):
        """Test valid second sense index returns correct sense."""
        entry = {
            "senses": [
                {"definition": "First sense definition"},
                {"definition": "Second sense definition"},
            ]
        }

        definition, sense = DictionaryService._get_definition_from_selection(entry, 1, -1)

        self.assertEqual(definition, "Second sense definition")
        self.assertEqual(sense.get("definition"), "Second sense definition")

    def test_subsense_selection_returns_subsense_definition(self):
        """Test subsense selection (subsense_idx >= 0) returns subsense definition."""
        entry = {
            "senses": [
                {
                    "definition": "Main sense definition",
                    "subsenses": [
                        {"definition": "Subsense 0 definition"},
                        {"definition": "Subsense 1 definition"},
                    ]
                }
            ]
        }

        definition, sense = DictionaryService._get_definition_from_selection(
            entry, 0, 0
        )

        self.assertEqual(definition, "Subsense 0 definition")
        # Returned sense should be the parent sense
        self.assertEqual(sense.get("definition"), "Main sense definition")

    def test_valid_second_subsense_selection(self):
        """Test selecting second subsense returns correct definition."""
        entry = {
            "senses": [
                {
                    "definition": "Main sense definition",
                    "subsenses": [
                        {"definition": "Subsense 0 definition"},
                        {"definition": "Subsense 1 definition"},
                    ]
                }
            ]
        }

        definition, sense = DictionaryService._get_definition_from_selection(
            entry, 0, 1
        )

        self.assertEqual(definition, "Subsense 1 definition")
        self.assertEqual(sense.get("definition"), "Main sense definition")

    def test_out_of_bounds_sense_idx_returns_empty_and_none(self):
        """Test out-of-bounds sense_idx returns ('', None)."""
        entry = {
            "senses": [
                {"definition": "First sense definition"},
            ]
        }

        definition, sense = DictionaryService._get_definition_from_selection(
            entry, 5, -1
        )

        self.assertEqual(definition, "")
        self.assertIsNone(sense)

    def test_out_of_bounds_sense_idx_multiple_senses(self):
        """Test out-of-bounds sense_idx with multiple senses."""
        entry = {
            "senses": [
                {"definition": "Sense 0"},
                {"definition": "Sense 1"},
                {"definition": "Sense 2"},
            ]
        }

        definition, sense = DictionaryService._get_definition_from_selection(
            entry, 10, -1
        )

        self.assertEqual(definition, "")
        self.assertIsNone(sense)

    def test_out_of_bounds_subsense_idx_falls_back_to_sense_definition(self):
        """Test out-of-bounds subsense_idx falls back to sense definition."""
        entry = {
            "senses": [
                {
                    "definition": "Main sense definition",
                    "subsenses": [
                        {"definition": "Subsense 0 definition"},
                    ]
                }
            ]
        }

        definition, sense = DictionaryService._get_definition_from_selection(
            entry, 0, 99
        )

        # Should fall back to sense-level definition
        self.assertEqual(definition, "Main sense definition")
        self.assertEqual(sense.get("definition"), "Main sense definition")

    def test_subsense_idx_minus_one_returns_sense_definition(self):
        """Test subsense_idx = -1 returns sense-level definition."""
        entry = {
            "senses": [
                {
                    "definition": "Main sense definition",
                    "subsenses": [
                        {"definition": "Subsense 0 definition"},
                    ]
                }
            ]
        }

        definition, sense = DictionaryService._get_definition_from_selection(
            entry, 0, -1
        )

        self.assertEqual(definition, "Main sense definition")
        self.assertEqual(sense.get("definition"), "Main sense definition")

    def test_entry_with_empty_senses_list(self):
        """Test entry with empty senses list returns empty and None."""
        entry = {"senses": []}

        definition, sense = DictionaryService._get_definition_from_selection(
            entry, 0, -1
        )

        self.assertEqual(definition, "")
        self.assertIsNone(sense)

    def test_entry_with_no_senses_key(self):
        """Test entry without senses key returns empty and None."""
        entry = {}

        definition, sense = DictionaryService._get_definition_from_selection(
            entry, 0, -1
        )

        self.assertEqual(definition, "")
        self.assertIsNone(sense)

    def test_sense_without_definition_field(self):
        """Test sense without definition field returns empty string."""
        entry = {
            "senses": [
                {"example": "some example"}  # No definition field
            ]
        }

        definition, sense = DictionaryService._get_definition_from_selection(
            entry, 0, -1
        )

        self.assertEqual(definition, "")
        self.assertIsNotNone(sense)

    def test_subsense_without_definition_field(self):
        """Test subsense without definition field returns empty string."""
        entry = {
            "senses": [
                {
                    "definition": "Main sense definition",
                    "subsenses": [
                        {"example": "subsense example"}  # No definition
                    ]
                }
            ]
        }

        definition, sense = DictionaryService._get_definition_from_selection(
            entry, 0, 0
        )

        self.assertEqual(definition, "")
        # Returned sense should still be the parent sense
        self.assertEqual(sense.get("definition"), "Main sense definition")

    def test_sense_with_empty_subsenses_list(self):
        """Test sense with empty subsenses list falls back to sense definition."""
        entry = {
            "senses": [
                {
                    "definition": "Main sense definition",
                    "subsenses": []  # Empty
                }
            ]
        }

        definition, sense = DictionaryService._get_definition_from_selection(
            entry, 0, 0
        )

        # Should fall back to sense-level definition when subsense index invalid
        self.assertEqual(definition, "Main sense definition")
        self.assertEqual(sense.get("definition"), "Main sense definition")

    def test_sense_without_subsenses_field(self):
        """Test sense without subsenses field falls back to sense definition."""
        entry = {
            "senses": [
                {"definition": "Main sense definition"}  # No subsenses field
            ]
        }

        definition, sense = DictionaryService._get_definition_from_selection(
            entry, 0, 0
        )

        self.assertEqual(definition, "Main sense definition")
        self.assertEqual(sense.get("definition"), "Main sense definition")

    def test_multiple_senses_with_varying_subsenses(self):
        """Test selecting from entry with varying subsense counts."""
        entry = {
            "senses": [
                {
                    "definition": "Sense 0",
                    "subsenses": [
                        {"definition": "Sub 0.0"},
                        {"definition": "Sub 0.1"},
                    ]
                },
                {
                    "definition": "Sense 1",
                    "subsenses": [
                        {"definition": "Sub 1.0"},
                    ]
                },
                {
                    "definition": "Sense 2"
                    # No subsenses
                }
            ]
        }

        # Select sense 1, subsense 0
        definition, sense = DictionaryService._get_definition_from_selection(
            entry, 1, 0
        )
        self.assertEqual(definition, "Sub 1.0")

        # Select sense 2 with subsense (should fall back to sense)
        definition, sense = DictionaryService._get_definition_from_selection(
            entry, 2, 0
        )
        self.assertEqual(definition, "Sense 2")

    def test_complex_sense_structure_with_additional_fields(self):
        """Test sense dict with complex structure including other fields."""
        entry = {
            "senses": [
                {
                    "definition": "Main definition",
                    "examples": ["Example 1", "Example 2"],
                    "synonyms": ["word1", "word2"],
                    "antonyms": ["opposite"],
                    "subsenses": [
                        {
                            "definition": "Sub definition",
                            "examples": ["Sub example"],
                        }
                    ]
                }
            ]
        }

        definition, sense = DictionaryService._get_definition_from_selection(
            entry, 0, 0
        )

        self.assertEqual(definition, "Sub definition")
        self.assertIn("examples", sense)
        self.assertIn("synonyms", sense)
        self.assertIn("antonyms", sense)

    def test_zero_index_sense_zero_index_subsense(self):
        """Test accessing first sense with first subsense."""
        entry = {
            "senses": [
                {
                    "definition": "First main",
                    "subsenses": [
                        {"definition": "First sub"}
                    ]
                }
            ]
        }

        definition, sense = DictionaryService._get_definition_from_selection(
            entry, 0, 0
        )

        self.assertEqual(definition, "First sub")
        self.assertEqual(sense["definition"], "First main")

    def test_large_sense_and_subsense_indices(self):
        """Test behavior with large out-of-bounds indices."""
        entry = {
            "senses": [
                {"definition": "Only sense"}
            ]
        }

        definition, sense = DictionaryService._get_definition_from_selection(
            entry, 1000, 1000
        )

        self.assertEqual(definition, "")
        self.assertIsNone(sense)

    def test_negative_subsense_index_with_valid_sense(self):
        """Test negative subsense_idx with valid sense returns sense definition."""
        entry = {
            "senses": [
                {
                    "definition": "Sense definition",
                    "subsenses": [
                        {"definition": "Subsense definition"}
                    ]
                }
            ]
        }

        definition, sense = DictionaryService._get_definition_from_selection(
            entry, 0, -2
        )

        # Negative subsense_idx not in [0, len(subsenses)) should fall back
        self.assertEqual(definition, "Sense definition")


class TestParseEntrySenseResponse(unittest.TestCase):
    """Test _parse_entry_sense_response static method with edge cases."""

    def test_xy_format_parsing(self):
        """Test X.Y format parsing returns correct indices."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {"definition": "sense 0"},
                {"definition": "sense 1"},
            ]},
            {"partOfSpeech": "verb", "senses": [
                {"definition": "verb sense"},
            ]},
        ]

        ei, si, ssi = DictionaryService._parse_entry_sense_response("0.1", entries)

        self.assertEqual((ei, si, ssi), (0, 1, -1))

    def test_xyz_format_parsing(self):
        """Test X.Y.Z format parsing returns correct indices."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {
                    "definition": "sense 0",
                    "subsenses": [
                        {"definition": "sub 0"},
                        {"definition": "sub 1"},
                    ]
                }
            ]},
        ]

        ei, si, ssi = DictionaryService._parse_entry_sense_response("0.0.1", entries)

        self.assertEqual((ei, si, ssi), (0, 0, 1))

    def test_no_match_returns_defaults(self):
        """Test no regex match returns (0, 0, -1)."""
        entries = [
            {"partOfSpeech": "noun", "senses": [{"definition": "sense"}]},
        ]

        ei, si, ssi = DictionaryService._parse_entry_sense_response(
            "No valid response", entries
        )

        self.assertEqual((ei, si, ssi), (0, 0, -1))

    def test_partial_match_no_format_returns_defaults(self):
        """Test content without X.Y format returns defaults."""
        entries = [
            {"partOfSpeech": "noun", "senses": [{"definition": "sense"}]},
        ]

        ei, si, ssi = DictionaryService._parse_entry_sense_response(
            "Definition number 5 is best", entries
        )

        self.assertEqual((ei, si, ssi), (0, 0, -1))

    def test_out_of_bounds_entry_clamping(self):
        """Test out-of-bounds entry index is clamped to max."""
        entries = [
            {"partOfSpeech": "noun", "senses": [{"definition": "sense 0"}]},
            {"partOfSpeech": "verb", "senses": [{"definition": "verb sense"}]},
        ]

        ei, si, ssi = DictionaryService._parse_entry_sense_response("5.0", entries)

        # Entry 5 should clamp to 1 (max index for 2 entries)
        self.assertEqual(ei, 1)
        self.assertEqual(si, 0)
        self.assertEqual(ssi, -1)

    def test_out_of_bounds_sense_clamping(self):
        """Test out-of-bounds sense index is clamped to max."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {"definition": "sense 0"},
                {"definition": "sense 1"},
                {"definition": "sense 2"},
            ]},
        ]

        ei, si, ssi = DictionaryService._parse_entry_sense_response("0.10", entries)

        # Sense 10 should clamp to 2 (max index for 3 senses)
        self.assertEqual(ei, 0)
        self.assertEqual(si, 2)
        self.assertEqual(ssi, -1)

    def test_out_of_bounds_subsense_clamping(self):
        """Test out-of-bounds subsense index is clamped to max."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {
                    "definition": "sense 0",
                    "subsenses": [
                        {"definition": "sub 0"},
                        {"definition": "sub 1"},
                    ]
                }
            ]},
        ]

        ei, si, ssi = DictionaryService._parse_entry_sense_response(
            "0.0.10", entries
        )

        # Subsense 10 should clamp to 1 (max index for 2 subsenses)
        self.assertEqual(ei, 0)
        self.assertEqual(si, 0)
        self.assertEqual(ssi, 1)

    def test_entry_with_empty_senses_list(self):
        """Test entry with empty senses list handles gracefully."""
        entries = [
            {"partOfSpeech": "noun", "senses": []}
        ]

        ei, si, ssi = DictionaryService._parse_entry_sense_response("0.0", entries)

        # Should handle gracefully with defaults
        self.assertEqual(ei, 0)
        self.assertEqual(si, 0)
        self.assertEqual(ssi, -1)

    def test_sense_without_subsenses_field(self):
        """Test sense without subsenses field returns -1 for subsense_idx."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {"definition": "sense 0"}  # No subsenses field
            ]},
        ]

        ei, si, ssi = DictionaryService._parse_entry_sense_response(
            "0.0.1", entries
        )

        # Should return -1 when subsenses don't exist
        self.assertEqual(ei, 0)
        self.assertEqual(si, 0)
        self.assertEqual(ssi, -1)

    def test_sense_with_empty_subsenses_list(self):
        """Test sense with empty subsenses list returns -1."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {"definition": "sense 0", "subsenses": []}
            ]},
        ]

        ei, si, ssi = DictionaryService._parse_entry_sense_response(
            "0.0.1", entries
        )

        # Empty subsenses should return -1
        self.assertEqual(ei, 0)
        self.assertEqual(si, 0)
        self.assertEqual(ssi, -1)

    def test_xy_without_subsense_part(self):
        """Test X.Y format without Z part returns -1 for subsense."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {
                    "definition": "sense 0",
                    "subsenses": [{"definition": "sub 0"}]
                }
            ]},
        ]

        ei, si, ssi = DictionaryService._parse_entry_sense_response("0.0", entries)

        # Without Z part, subsense should be -1
        self.assertEqual(ei, 0)
        self.assertEqual(si, 0)
        self.assertEqual(ssi, -1)

    def test_text_with_embedded_xy_format(self):
        """Test regex finds X.Y format embedded in surrounding text."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {"definition": "sense 0"},
                {"definition": "sense 1"},
            ]},
        ]

        ei, si, ssi = DictionaryService._parse_entry_sense_response(
            "Answer is 0.1, the best match", entries
        )

        # Should find 0.1 in the text
        self.assertEqual((ei, si, ssi), (0, 1, -1))

    def test_multiple_xy_formats_uses_first_match(self):
        """Test multiple X.Y formats uses first match."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {"definition": "sense 0"},
                {"definition": "sense 1"},
            ]},
            {"partOfSpeech": "verb", "senses": [
                {"definition": "verb sense 0"},
            ]},
        ]

        ei, si, ssi = DictionaryService._parse_entry_sense_response(
            "0.1 or maybe 1.0", entries
        )

        # Should use first match (0.1)
        self.assertEqual((ei, si, ssi), (0, 1, -1))

    def test_zero_zero_subsense_is_valid(self):
        """Test 0.0.0 parsing returns (0, 0, 0)."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {
                    "definition": "sense 0",
                    "subsenses": [
                        {"definition": "sub 0"},
                    ]
                }
            ]},
        ]

        ei, si, ssi = DictionaryService._parse_entry_sense_response(
            "0.0.0", entries
        )

        self.assertEqual((ei, si, ssi), (0, 0, 0))

    def test_multidigit_indices(self):
        """Test parsing multi-digit indices."""
        # Create multiple entries with multi-digit sense/subsense counts
        entries = [
            {
                "partOfSpeech": f"pos{i}",
                "senses": [
                    {
                        "definition": f"sense {j}",
                        "subsenses": [
                            {"definition": f"sub {k}"}
                            for k in range(12)
                        ]
                    }
                    for j in range(12)
                ]
            }
            for i in range(11)
        ]

        ei, si, ssi = DictionaryService._parse_entry_sense_response(
            "10.11.15", entries
        )

        # Entry 10 exists, sense 11 exists, subsense 15 clamped to 11 (max index for 12 subsenses)
        self.assertEqual(ei, 10)
        self.assertEqual(si, 11)
        self.assertEqual(ssi, 11)  # clamped from 15 to max index 11

    def test_leading_zeros_in_indices(self):
        """Test parsing indices with leading zeros."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {"definition": "sense 0"},
                {"definition": "sense 1"},
            ]},
        ]

        ei, si, ssi = DictionaryService._parse_entry_sense_response(
            "00.01", entries
        )

        # Leading zeros should be parsed as 0 and 1
        self.assertEqual((ei, si, ssi), (0, 1, -1))

    def test_negative_entry_index_not_matched(self):
        """Test negative entry index is not matched by regex."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {"definition": "sense 0"},
            ]},
        ]

        ei, si, ssi = DictionaryService._parse_entry_sense_response(
            "-1.0", entries
        )

        # Negative index should not be matched
        self.assertEqual((ei, si, ssi), (0, 0, -1))

    def test_single_entry_single_sense_no_subsenses(self):
        """Test single entry with single sense and no subsenses."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {"definition": "the only sense"}
            ]},
        ]

        ei, si, ssi = DictionaryService._parse_entry_sense_response(
            "0.0", entries
        )

        self.assertEqual((ei, si, ssi), (0, 0, -1))

    def test_complex_entries_multiple_parts_of_speech(self):
        """Test complex entries with multiple parts of speech."""
        entries = [
            {
                "partOfSpeech": "noun",
                "senses": [
                    {
                        "definition": "noun sense 0",
                        "subsenses": [
                            {"definition": "noun sub 0.0"},
                            {"definition": "noun sub 0.1"},
                        ]
                    },
                    {"definition": "noun sense 1"},
                ]
            },
            {
                "partOfSpeech": "verb",
                "senses": [
                    {
                        "definition": "verb sense 0",
                        "subsenses": [{"definition": "verb sub 0.0"}]
                    },
                ]
            },
            {
                "partOfSpeech": "adjective",
                "senses": [
                    {"definition": "adj sense 0"},
                ]
            },
        ]

        # Test selecting from verb entry
        ei, si, ssi = DictionaryService._parse_entry_sense_response(
            "1.0.0", entries
        )
        self.assertEqual((ei, si, ssi), (1, 0, 0))

        # Test selecting from adjective entry
        ei, si, ssi = DictionaryService._parse_entry_sense_response(
            "2.0", entries
        )
        self.assertEqual((ei, si, ssi), (2, 0, -1))

    def test_entry_index_clamping_boundary(self):
        """Test entry index clamping at exact boundary."""
        entries = [
            {"partOfSpeech": "noun", "senses": [{"definition": "sense 0"}]},
            {"partOfSpeech": "verb", "senses": [{"definition": "sense 0"}]},
        ]

        # Entry 2 should clamp to 1 (last valid index)
        ei, si, ssi = DictionaryService._parse_entry_sense_response("2.0", entries)
        self.assertEqual(ei, 1)

        # Entry 1 should be valid
        ei, si, ssi = DictionaryService._parse_entry_sense_response("1.0", entries)
        self.assertEqual(ei, 1)

    def test_sense_index_clamping_boundary(self):
        """Test sense index clamping at exact boundary."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {"definition": "sense 0"},
                {"definition": "sense 1"},
                {"definition": "sense 2"},
            ]},
        ]

        # Sense 3 should clamp to 2 (last valid index)
        ei, si, ssi = DictionaryService._parse_entry_sense_response("0.3", entries)
        self.assertEqual(si, 2)

        # Sense 2 should be valid
        ei, si, ssi = DictionaryService._parse_entry_sense_response("0.2", entries)
        self.assertEqual(si, 2)

    def test_subsense_index_clamping_boundary(self):
        """Test subsense index clamping at exact boundary."""
        entries = [
            {"partOfSpeech": "noun", "senses": [
                {
                    "definition": "sense 0",
                    "subsenses": [
                        {"definition": "sub 0"},
                        {"definition": "sub 1"},
                    ]
                }
            ]},
        ]

        # Subsense 2 should clamp to 1 (last valid index)
        ei, si, ssi = DictionaryService._parse_entry_sense_response(
            "0.0.2", entries
        )
        self.assertEqual(ssi, 1)

        # Subsense 1 should be valid
        ei, si, ssi = DictionaryService._parse_entry_sense_response(
            "0.0.1", entries
        )
        self.assertEqual(ssi, 1)


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
