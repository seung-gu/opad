"""Unit tests for sense selection service — Step 2 of dictionary lookup.

Tests cover:
- select_best_sense() trivial path (no LLM call, returns DEFAULT_LABEL)
- select_best_sense() LLM path (calls LLM, returns LLM label + stats)
- select_best_sense() error fallback (LLM fails, returns DEFAULT_LABEL)
- _pick_sense() with build_sense_listing returning None (trivial)
- _pick_sense() with build_sense_listing returning string (non-trivial)
- prompt construction includes sentence, word, and listing
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from domain.model.token_usage import LLMCallResult
from domain.model.vocabulary import SenseResult
from adapter.fake.dictionary import FakeDictionaryAdapter
from adapter.fake.llm import FakeLLMAdapter
from services.sense_selection import (
    select_best_sense, _build_sense_prompt, DEFAULT_LABEL,
)


class TestSelectBestSenseEmptyEntries(unittest.TestCase):
    """Tests for select_best_sense() with empty entries."""

    def setUp(self):
        """Set up test fixtures."""
        self.dictionary = FakeDictionaryAdapter()
        self.llm = FakeLLMAdapter()

    def test_empty_entries_returns_empty_sense_and_default_label(self):
        """Empty entries returns empty SenseResult and DEFAULT_LABEL, no LLM call."""
        async def run_test():
            result, label, stats = await select_best_sense(
                sentence="A sentence",
                word="word",
                entries=[],
                dictionary=self.dictionary,
                llm=self.llm,
            )
            self.assertIsInstance(result, SenseResult)
            self.assertEqual(result.definition, "")
            self.assertIsNone(result.examples)
            self.assertEqual(label, DEFAULT_LABEL)
            self.assertIsNone(stats)

        import asyncio
        asyncio.run(run_test())


class TestSelectBestSenseTrivialPath(unittest.TestCase):
    """Tests for select_best_sense() trivial case (no LLM needed)."""

    def setUp(self):
        """Set up test fixtures."""
        self.dictionary = FakeDictionaryAdapter()
        self.llm = FakeLLMAdapter()

    def test_trivial_single_sense_no_llm_call(self):
        """Trivial entries skip LLM, return DEFAULT_LABEL with SenseResult."""
        entries = [
            {
                "senses": [
                    {
                        "definition": "Single definition",
                        "examples": ["Example 1"],
                    }
                ]
            }
        ]

        async def run_test():
            result, label, stats = await select_best_sense(
                sentence="The sentence context",
                word="word",
                entries=entries,
                dictionary=self.dictionary,
                llm=self.llm,
            )
            # Should return the sense without LLM call
            self.assertEqual(result.definition, "Single definition")
            self.assertEqual(result.examples, ["Example 1"])
            self.assertEqual(label, DEFAULT_LABEL)
            self.assertIsNone(stats)  # No LLM call = no stats

        import asyncio
        asyncio.run(run_test())

    def test_trivial_returns_sense_from_default_label(self):
        """Trivial case calls get_sense with DEFAULT_LABEL."""
        entries = [
            {
                "senses": [
                    {"definition": "The definition"}
                ]
            }
        ]

        async def run_test():
            result, label, stats = await select_best_sense(
                sentence="A sentence",
                word="test",
                entries=entries,
                dictionary=self.dictionary,
                llm=self.llm,
            )
            # get_sense should be called with DEFAULT_LABEL and entries
            # Verify definition matches what get_sense returns for 0.0
            self.assertEqual(result.definition, "The definition")
            self.assertEqual(label, DEFAULT_LABEL)

        import asyncio
        asyncio.run(run_test())


class TestSelectBestSenseLLMPath(unittest.TestCase):
    """Tests for select_best_sense() with LLM sense selection."""

    def setUp(self):
        """Set up test fixtures."""
        self.dictionary = FakeDictionaryAdapter()

    def test_non_trivial_calls_llm_and_returns_label(self):
        """Non-trivial entries call LLM and use its label for sense extraction."""
        entries = [
            {
                "senses": [
                    {
                        "definition": "Definition 1",
                        "examples": ["Ex1"],
                    },
                    {
                        "definition": "Definition 2",
                        "examples": ["Ex2"],
                    },
                ]
            }
        ]
        # Create mock LLM
        mock_llm = AsyncMock()
        stats = LLMCallResult(
            model="gpt-4.1-mini",
            prompt_tokens=100,
            completion_tokens=10,
            total_tokens=110,
            estimated_cost=0.0001,
            provider="openai",
        )
        mock_llm.call.return_value = ("0.1", stats)

        async def run_test():
            result, label, returned_stats = await select_best_sense(
                sentence="The sentence context",
                word="word",
                entries=entries,
                dictionary=self.dictionary,
                llm=mock_llm,
            )
            # Should call LLM
            self.assertTrue(mock_llm.call.called)
            # Should return LLM's label
            self.assertEqual(label, "0.1")
            # Should extract sense for label 0.1
            self.assertEqual(result.definition, "Definition 2")
            self.assertEqual(result.examples, ["Ex2"])
            # Should return stats from LLM
            self.assertEqual(returned_stats, stats)

        import asyncio
        asyncio.run(run_test())

    def test_llm_call_parameters(self):
        """LLM is called with correct parameters."""
        entries = [
            {
                "senses": [
                    {"definition": "Def 1"},
                    {"definition": "Def 2"},
                ]
            }
        ]
        mock_llm = AsyncMock()
        stats = LLMCallResult(
            model="gpt-4.1-mini",
            prompt_tokens=100,
            completion_tokens=10,
            total_tokens=110,
            estimated_cost=0.0001,
            provider="openai",
        )
        mock_llm.call.return_value = ("0.0", stats)

        async def run_test():
            await select_best_sense(
                sentence="Test sentence",
                word="testword",
                entries=entries,
                dictionary=self.dictionary,
                llm=mock_llm,
                model="openai/gpt-4.1-mini",
            )
            # Verify LLM was called
            mock_llm.call.assert_called_once()
            # Get the call arguments
            call_kwargs = mock_llm.call.call_args[1]
            self.assertEqual(call_kwargs["model"], "openai/gpt-4.1-mini")
            self.assertEqual(call_kwargs["temperature"], 0)
            self.assertEqual(call_kwargs["timeout"], 15)
            self.assertEqual(call_kwargs["max_tokens"], 10)

        import asyncio
        asyncio.run(run_test())

    def test_llm_prompt_includes_sentence_word_and_listing(self):
        """LLM prompt includes sentence, word, and sense listing."""
        entries = [
            {
                "senses": [
                    {"definition": "Def 1"},
                    {"definition": "Def 2"},
                ]
            }
        ]
        mock_llm = AsyncMock()
        stats = LLMCallResult(
            model="gpt-4.1-mini",
            prompt_tokens=100,
            completion_tokens=10,
            total_tokens=110,
            estimated_cost=0.0001,
            provider="openai",
        )
        mock_llm.call.return_value = ("0.0", stats)

        async def run_test():
            await select_best_sense(
                sentence="My test sentence",
                word="myword",
                entries=entries,
                dictionary=self.dictionary,
                llm=mock_llm,
            )
            # Get the prompt from LLM call
            call_args = mock_llm.call.call_args[1]
            messages = call_args["messages"]
            prompt = messages[0]["content"]
            # Verify prompt contains required elements
            self.assertIn("My test sentence", prompt)
            self.assertIn("myword", prompt)
            self.assertIn("0.0 Def 1", prompt)
            self.assertIn("0.1 Def 2", prompt)

        import asyncio
        asyncio.run(run_test())


class TestSelectBestSenseErrorFallback(unittest.TestCase):
    """Tests for select_best_sense() error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.dictionary = FakeDictionaryAdapter()

    def test_llm_exception_falls_back_to_default(self):
        """LLM exception causes fallback to DEFAULT_LABEL."""
        entries = [
            {
                "senses": [
                    {"definition": "Def 1"},
                    {"definition": "Def 2"},
                ]
            }
        ]
        mock_llm = AsyncMock()
        mock_llm.call.side_effect = RuntimeError("LLM failed")

        async def run_test():
            result, label, stats = await select_best_sense(
                sentence="A sentence",
                word="word",
                entries=entries,
                dictionary=self.dictionary,
                llm=mock_llm,
            )
            # Should return DEFAULT_LABEL on error
            self.assertEqual(label, DEFAULT_LABEL)
            # Should return sense for DEFAULT_LABEL
            self.assertEqual(result.definition, "Def 1")
            # Should not have stats
            self.assertIsNone(stats)

        import asyncio
        asyncio.run(run_test())

    def test_llm_timeout_falls_back_to_default(self):
        """LLM timeout causes fallback to DEFAULT_LABEL."""
        entries = [
            {
                "senses": [
                    {"definition": "Def 1"},
                ]
            }
        ]
        mock_llm = AsyncMock()
        mock_llm.call.side_effect = TimeoutError("LLM timeout")

        async def run_test():
            result, label, stats = await select_best_sense(
                sentence="A sentence",
                word="word",
                entries=entries,
                dictionary=self.dictionary,
                llm=mock_llm,
            )
            # Should fallback gracefully
            self.assertEqual(label, DEFAULT_LABEL)
            self.assertIsNone(stats)

        import asyncio
        asyncio.run(run_test())

    def test_llm_error_returns_consistent_fallback(self):
        """LLM error returns consistent fallback."""
        entries = [
            {
                "senses": [
                    {"definition": "Def 1"},
                    {"definition": "Def 2"},
                ]
            }
        ]
        mock_llm = AsyncMock()
        mock_llm.call.side_effect = ValueError("LLM error")

        async def run_test():
            result1, label1, stats1 = await select_best_sense(
                sentence="A sentence",
                word="word",
                entries=entries,
                dictionary=self.dictionary,
                llm=mock_llm,
            )
            # Reset mock and try again
            mock_llm.call.side_effect = RuntimeError("Different error")
            result2, label2, stats2 = await select_best_sense(
                sentence="A sentence",
                word="word",
                entries=entries,
                dictionary=self.dictionary,
                llm=mock_llm,
            )
            # Both should use DEFAULT_LABEL on any LLM error
            self.assertEqual(label1, DEFAULT_LABEL)
            self.assertEqual(label2, DEFAULT_LABEL)
            self.assertIsNone(stats1)
            self.assertIsNone(stats2)

        import asyncio
        asyncio.run(run_test())


class TestBuildSensePrompt(unittest.TestCase):
    """Tests for _build_sense_prompt() — prompt construction."""

    def test_prompt_includes_sentence(self):
        """Prompt includes the sentence."""
        prompt = _build_sense_prompt(
            sentence="The quick brown fox",
            word="fox",
            listing="0.0 Definition",
        )
        self.assertIn("The quick brown fox", prompt)

    def test_prompt_includes_word(self):
        """Prompt includes the word."""
        prompt = _build_sense_prompt(
            sentence="The sentence",
            word="testword",
            listing="0.0 Definition",
        )
        self.assertIn("testword", prompt)

    def test_prompt_includes_listing(self):
        """Prompt includes the sense listing."""
        listing = "0.0 Definition 1\n0.1 Definition 2"
        prompt = _build_sense_prompt(
            sentence="The sentence",
            word="word",
            listing=listing,
        )
        self.assertIn("Definition 1", prompt)
        self.assertIn("Definition 2", prompt)

    def test_prompt_includes_instructions(self):
        """Prompt includes LLM instructions."""
        prompt = _build_sense_prompt(
            sentence="The sentence",
            word="word",
            listing="0.0 Definition",
        )
        self.assertIn("Which definition best matches", prompt)
        self.assertIn("Reply with the number only", prompt)

    def test_prompt_format_is_consistent(self):
        """Prompt format is consistent across calls."""
        prompt1 = _build_sense_prompt(
            sentence="Test",
            word="word",
            listing="List",
        )
        prompt2 = _build_sense_prompt(
            sentence="Test",
            word="word",
            listing="List",
        )
        self.assertEqual(prompt1, prompt2)


if __name__ == "__main__":
    unittest.main()
