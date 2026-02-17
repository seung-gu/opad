"""Tests for sense selection module — Step 2 of dictionary lookup pipeline.

Tests cover:
1. select_best_sense() — full flow
2. _select_entry_sense() — single entry skip, LLM call, exception handling
3. _build_sense_prompt() — formatting with entries/senses/subsenses
4. _parse_sense_response() — X.Y, X.Y.Z parsing, clamping
5. _get_definition_from_selection() — sense/subsense extraction
6. _extract_examples() — string examples, dict examples, max limit
7. SenseResult dataclass defaults
8. Error handling and edge cases
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adapter.fake.llm import FakeLLMAdapter
from utils.sense_selection import (
    select_best_sense,
    SenseResult,
    _select_entry_sense,
    _build_sense_prompt,
    _parse_sense_response,
    _get_definition_from_selection,
    _extract_examples,
)
from domain.model.token_usage import LLMCallResult


class TestSenseResultDataclass(unittest.TestCase):
    """Test SenseResult dataclass defaults."""

    def test_default_values(self):
        """Test SenseResult default values."""
        result = SenseResult()

        assert result.entry_idx == 0
        assert result.sense_idx == 0
        assert result.subsense_idx == -1
        assert result.definition == ""
        assert result.examples is None
        assert result.stats is None

    def test_custom_values(self):
        """Test SenseResult with custom values."""
        stats = LLMCallResult(
            model="gpt-4", prompt_tokens=10, completion_tokens=2,
            total_tokens=12, estimated_cost=0.0001
        )
        result = SenseResult(
            entry_idx=1,
            sense_idx=2,
            subsense_idx=3,
            definition="test def",
            examples=["ex1", "ex2"],
            stats=stats
        )

        assert result.entry_idx == 1
        assert result.sense_idx == 2
        assert result.subsense_idx == 3
        assert result.definition == "test def"
        assert result.examples == ["ex1", "ex2"]
        assert result.stats == stats


class TestSelectBestSense(unittest.IsolatedAsyncioTestCase):
    """Test select_best_sense full flow."""

    async def test_empty_entries_returns_defaults(self):
        """Test empty entries list returns default SenseResult."""
        result = await select_best_sense("Sentence", "word", [], FakeLLMAdapter())

        assert isinstance(result, SenseResult)
        assert result.entry_idx == 0
        assert result.sense_idx == 0
        assert result.subsense_idx == -1
        assert result.definition == ""
        assert result.examples is None
        assert result.stats is None

    @patch('utils.sense_selection._select_entry_sense')
    @patch('utils.sense_selection._get_definition_from_selection')
    @patch('utils.sense_selection._extract_examples')
    async def test_single_entry_single_sense_skips_llm(self, mock_examples, mock_def, mock_select):
        """Test single entry/sense returns defaults without LLM call."""
        entries = [{"partOfSpeech": "noun", "senses": [{"definition": "only sense"}]}]
        mock_select.return_value = (0, 0, -1, None)
        mock_def.return_value = ("only sense", {"definition": "only sense"})
        mock_examples.return_value = None

        result = await select_best_sense("Sentence", "word", entries, FakeLLMAdapter())

        assert result.entry_idx == 0
        assert result.sense_idx == 0
        assert result.subsense_idx == -1
        assert result.definition == "only sense"
        mock_select.assert_called_once()

    @patch('utils.sense_selection._select_entry_sense')
    @patch('utils.sense_selection._get_definition_from_selection')
    @patch('utils.sense_selection._extract_examples')
    async def test_multiple_senses_calls_llm(self, mock_examples, mock_def, mock_select):
        """Test multiple senses triggers LLM call."""
        entries = [{
            "partOfSpeech": "noun",
            "senses": [
                {"definition": "sense 1"},
                {"definition": "sense 2"},
            ]
        }]
        stats = LLMCallResult(
            model="gpt-4", prompt_tokens=50, completion_tokens=3,
            total_tokens=53, estimated_cost=0.001
        )
        mock_select.return_value = (0, 1, -1, stats)
        mock_def.return_value = ("sense 2", {"definition": "sense 2"})
        mock_examples.return_value = ["example 1"]

        result = await select_best_sense("Sentence", "word", entries, FakeLLMAdapter())

        assert result.entry_idx == 0
        assert result.sense_idx == 1
        assert result.definition == "sense 2"
        assert result.examples == ["example 1"]
        assert result.stats == stats

    @patch('utils.sense_selection._select_entry_sense')
    @patch('utils.sense_selection._get_definition_from_selection')
    @patch('utils.sense_selection._extract_examples')
    async def test_subsense_extraction(self, mock_examples, mock_def, mock_select):
        """Test subsense selection and extraction."""
        entries = [{
            "partOfSpeech": "noun",
            "senses": [{
                "definition": "main",
                "subsenses": [
                    {"definition": "subsense 0"},
                    {"definition": "subsense 1"},
                ]
            }]
        }]
        stats = LLMCallResult(
            model="gpt-4", prompt_tokens=50, completion_tokens=3,
            total_tokens=53, estimated_cost=0.001
        )
        mock_select.return_value = (0, 0, 1, stats)
        mock_def.return_value = ("subsense 1", {"definition": "subsense 1"})
        mock_examples.return_value = None

        result = await select_best_sense("Sentence", "word", entries, FakeLLMAdapter())

        assert result.subsense_idx == 1
        assert result.definition == "subsense 1"


class TestSelectEntrySense(unittest.IsolatedAsyncioTestCase):
    """Test _select_entry_sense function."""

    async def test_single_entry_single_sense_no_subsenses_skips_llm(self):
        """Test trivial case (1 entry, 1 sense, 0 subsenses) skips LLM."""
        entries = [{"partOfSpeech": "noun", "senses": [{"definition": "only"}]}]

        ei, si, ssi, stats = await _select_entry_sense("Sentence", "word", entries, FakeLLMAdapter(), "gpt-4")

        assert (ei, si, ssi) == (0, 0, -1)
        assert stats is None

    async def test_single_entry_multiple_senses_calls_llm(self):
        """Test multiple senses triggers LLM."""
        entries = [{
            "partOfSpeech": "noun",
            "senses": [
                {"definition": "sense 1"},
                {"definition": "sense 2"},
            ]
        }]

        stats = LLMCallResult(
            model="gpt-4", prompt_tokens=50, completion_tokens=3,
            total_tokens=53, estimated_cost=0.001
        )
        fake_llm = FakeLLMAdapter(response="0.1", stats=stats)

        ei, si, ssi, returned_stats = await _select_entry_sense(
            "Sentence", "word", entries, fake_llm, "gpt-4"
        )

        assert (ei, si, ssi) == (0, 1, -1)
        assert returned_stats == stats
        assert len(fake_llm.calls) == 1

    async def test_multiple_entries_calls_llm(self):
        """Test multiple entries triggers LLM."""
        entries = [
            {"partOfSpeech": "noun", "senses": [{"definition": "n1"}]},
            {"partOfSpeech": "verb", "senses": [{"definition": "v1"}]},
        ]

        stats = LLMCallResult(
            model="gpt-4", prompt_tokens=50, completion_tokens=3,
            total_tokens=53, estimated_cost=0.001
        )
        fake_llm = FakeLLMAdapter(response="1.0", stats=stats)

        ei, si, ssi, returned_stats = await _select_entry_sense(
            "Sentence", "word", entries, fake_llm, "gpt-4"
        )

        assert ei == 1
        assert len(fake_llm.calls) == 1

    async def test_single_entry_with_subsenses_calls_llm(self):
        """Test subsenses trigger LLM even with single entry/sense."""
        entries = [{
            "partOfSpeech": "noun",
            "senses": [{
                "definition": "main",
                "subsenses": [
                    {"definition": "sub1"},
                    {"definition": "sub2"},
                ]
            }]
        }]

        stats = LLMCallResult(
            model="gpt-4", prompt_tokens=50, completion_tokens=3,
            total_tokens=53, estimated_cost=0.001
        )
        fake_llm = FakeLLMAdapter(response="0.0.1", stats=stats)

        ei, si, ssi, returned_stats = await _select_entry_sense(
            "Sentence", "word", entries, fake_llm, "gpt-4"
        )

        assert (ei, si, ssi) == (0, 0, 1)
        assert len(fake_llm.calls) == 1

    async def test_llm_exception_returns_defaults(self):
        """Test LLM exception returns defaults."""
        entries = [
            {"partOfSpeech": "noun", "senses": [{"definition": "n1"}]},
            {"partOfSpeech": "verb", "senses": [{"definition": "v1"}]},
        ]
        failing_llm = MagicMock()
        failing_llm.call = AsyncMock(side_effect=Exception("API error"))

        ei, si, ssi, stats = await _select_entry_sense(
            "Sentence", "word", entries, failing_llm, "gpt-4"
        )

        assert (ei, si, ssi) == (0, 0, -1)
        assert stats is None


class TestBuildSensePrompt(unittest.TestCase):
    """Test building sense selection prompt."""

    def test_single_entry_single_sense_format(self):
        """Test prompt format with single entry/sense."""
        entries = [{
            "partOfSpeech": "noun",
            "senses": [{"definition": "the definition"}]
        }]

        prompt = _build_sense_prompt("Test sentence", "word", entries)

        assert "Test sentence" in prompt
        assert "word" in prompt
        assert "the definition" in prompt
        assert "entries[0]" in prompt

    def test_multiple_entries_format(self):
        """Test prompt format with multiple entries."""
        entries = [
            {"partOfSpeech": "noun", "senses": [{"definition": "def1"}]},
            {"partOfSpeech": "verb", "senses": [{"definition": "def2"}]},
        ]

        prompt = _build_sense_prompt("Sentence", "word", entries)

        assert "entries[0] (noun)" in prompt
        assert "entries[1] (verb)" in prompt
        assert "0.0" in prompt
        assert "1.0" in prompt

    def test_multiple_senses_format(self):
        """Test prompt format with multiple senses per entry."""
        entries = [{
            "partOfSpeech": "noun",
            "senses": [
                {"definition": "def1"},
                {"definition": "def2"},
            ]
        }]

        prompt = _build_sense_prompt("Sentence", "word", entries)

        assert "0.0" in prompt
        assert "0.1" in prompt
        assert "def1" in prompt
        assert "def2" in prompt

    def test_subsenses_format(self):
        """Test prompt format with subsenses."""
        entries = [{
            "partOfSpeech": "noun",
            "senses": [{
                "definition": "main",
                "subsenses": [
                    {"definition": "sub1"},
                    {"definition": "sub2"},
                ]
            }]
        }]

        prompt = _build_sense_prompt("Sentence", "word", entries)

        assert "0.0.0" in prompt
        assert "0.0.1" in prompt
        assert "sub1" in prompt
        assert "sub2" in prompt

    def test_missing_definitions_gracefully_handled(self):
        """Test prompt with missing definitions."""
        entries = [{
            "partOfSpeech": "noun",
            "senses": [{}]  # Missing 'definition' key
        }]

        prompt = _build_sense_prompt("Sentence", "word", entries)

        assert "entries[0]" in prompt
        assert "0.0" in prompt
        # Should not crash

    def test_missing_part_of_speech_defaults(self):
        """Test prompt with missing partOfSpeech."""
        entries = [{
            "senses": [{"definition": "def"}]
        }]

        prompt = _build_sense_prompt("Sentence", "word", entries)

        assert "unknown" in prompt.lower() or "entries[0]" in prompt


class TestParseSenseResponse(unittest.TestCase):
    """Test parsing LLM sense response."""

    def test_xy_parsing_simple(self):
        """Test X.Y format parsing."""
        entries = [
            {"partOfSpeech": "noun", "senses": [{"definition": "1"}, {"definition": "2"}]},
        ]

        ei, si, ssi = _parse_sense_response("0.1", entries)

        assert (ei, si, ssi) == (0, 1, -1)

    def test_xyz_parsing_subsense(self):
        """Test X.Y.Z format parsing for subsenses."""
        entries = [{
            "partOfSpeech": "noun",
            "senses": [{
                "definition": "main",
                "subsenses": [{"definition": "sub0"}, {"definition": "sub1"}]
            }]
        }]

        ei, si, ssi = _parse_sense_response("0.0.2", entries)

        assert (ei, si, ssi) == (0, 0, 1)  # subsense_idx clamped to 1

    def test_out_of_bounds_entry_clamped(self):
        """Test out-of-bounds entry index is clamped."""
        entries = [
            {"partOfSpeech": "noun", "senses": [{"definition": "1"}]},
        ]

        ei, si, ssi = _parse_sense_response("99.0", entries)

        assert ei == 0  # clamped to max

    def test_out_of_bounds_sense_clamped(self):
        """Test out-of-bounds sense index is clamped."""
        entries = [{
            "partOfSpeech": "noun",
            "senses": [{"definition": "1"}, {"definition": "2"}]
        }]

        ei, si, ssi = _parse_sense_response("0.99", entries)

        assert si == 1  # clamped to max

    def test_out_of_bounds_subsense_clamped(self):
        """Test out-of-bounds subsense index is clamped."""
        entries = [{
            "partOfSpeech": "noun",
            "senses": [{
                "definition": "main",
                "subsenses": [{"definition": "sub1"}]
            }]
        }]

        ei, si, ssi = _parse_sense_response("0.0.99", entries)

        assert ssi == 0  # clamped to max

    def test_invalid_format_returns_defaults(self):
        """Test invalid format returns (0, 0, -1)."""
        entries = [{"partOfSpeech": "noun", "senses": [{"definition": "1"}]}]

        ei, si, ssi = _parse_sense_response("invalid", entries)

        assert (ei, si, ssi) == (0, 0, -1)

    def test_no_number_format_returns_defaults(self):
        """Test response with no numbers returns defaults."""
        entries = [{"partOfSpeech": "noun", "senses": [{"definition": "1"}]}]

        ei, si, ssi = _parse_sense_response("The answer is sense 2", entries)

        assert (ei, si, ssi) == (0, 0, -1)

    def test_partial_match_xy_format(self):
        """Test regex matches X.Y within text."""
        entries = [
            {"partOfSpeech": "noun", "senses": [{"definition": "1"}, {"definition": "2"}]},
        ]

        ei, si, ssi = _parse_sense_response(
            "I think the answer is 0.1 because...", entries
        )

        assert (ei, si, ssi) == (0, 1, -1)

    def test_partial_match_xyz_format(self):
        """Test regex matches X.Y.Z within text."""
        entries = [{
            "partOfSpeech": "noun",
            "senses": [{
                "definition": "main",
                "subsenses": [{"definition": "sub1"}]
            }]
        }]

        ei, si, ssi = _parse_sense_response(
            "The best match is 0.0.0 in my opinion", entries
        )

        assert (ei, si, ssi) == (0, 0, 0)

    def test_negative_values_treated_as_zero(self):
        """Test negative regex matches don't occur (regex only matches digits)."""
        entries = [{"partOfSpeech": "noun", "senses": [{"definition": "1"}]}]

        ei, si, ssi = _parse_sense_response("-1.0", entries)

        # Regex should match nothing, return defaults
        assert (ei, si, ssi) == (0, 0, -1)

    def test_empty_response_returns_defaults(self):
        """Test empty response returns defaults."""
        entries = [{"partOfSpeech": "noun", "senses": [{"definition": "1"}]}]

        ei, si, ssi = _parse_sense_response("", entries)

        assert (ei, si, ssi) == (0, 0, -1)

    def test_sense_clamped_when_no_senses(self):
        """Test sense index is 0 when entry has no senses."""
        entries = [{"partOfSpeech": "noun"}]  # Missing 'senses' key

        ei, si, ssi = _parse_sense_response("0.0", entries)

        assert si == 0

    def test_subsense_clamped_when_no_subsenses(self):
        """Test subsense index is -1 when sense has no subsenses."""
        entries = [{
            "partOfSpeech": "noun",
            "senses": [{"definition": "main"}]  # Missing 'subsenses' key
        }]

        ei, si, ssi = _parse_sense_response("0.0.0", entries)

        assert ssi == -1


class TestGetDefinitionFromSelection(unittest.TestCase):
    """Test extracting definition from selection."""

    def test_main_sense_definition(self):
        """Test extracting main sense definition."""
        entry = {
            "senses": [
                {"definition": "sense 0"},
                {"definition": "sense 1"},
            ]
        }

        definition, sense = _get_definition_from_selection(entry, 1, -1)

        assert definition == "sense 1"
        assert sense == {"definition": "sense 1"}

    def test_subsense_definition(self):
        """Test extracting subsense definition."""
        entry = {
            "senses": [{
                "definition": "main",
                "subsenses": [
                    {"definition": "sub 0"},
                    {"definition": "sub 1"},
                ]
            }]
        }

        definition, sense = _get_definition_from_selection(entry, 0, 1)

        assert definition == "sub 1"
        assert sense is not None
        assert sense["definition"] == "main"

    def test_out_of_bounds_sense_returns_empty(self):
        """Test out-of-bounds sense index returns empty."""
        entry = {"senses": [{"definition": "only"}]}

        definition, sense = _get_definition_from_selection(entry, 99, -1)

        assert definition == ""
        assert sense is None

    def test_missing_senses_returns_empty(self):
        """Test missing senses key returns empty."""
        entry = {"partOfSpeech": "noun"}

        definition, sense = _get_definition_from_selection(entry, 0, -1)

        assert definition == ""
        assert sense is None

    def test_missing_definition_returns_empty_string(self):
        """Test missing definition returns empty string."""
        entry = {
            "senses": [{"partOfSpeech": "noun"}]  # Missing 'definition'
        }

        definition, sense = _get_definition_from_selection(entry, 0, -1)

        assert definition == ""
        assert sense == {"partOfSpeech": "noun"}

    def test_subsense_without_subsenses_returns_main_sense(self):
        """Test requesting subsense when sense has none."""
        entry = {
            "senses": [{"definition": "main"}]  # No subsenses
        }

        definition, sense = _get_definition_from_selection(entry, 0, 0)

        assert definition == "main"

    def test_zero_sense_zero_subsense(self):
        """Test accessing first sense, first subsense."""
        entry = {
            "senses": [{
                "definition": "main",
                "subsenses": [{"definition": "first sub"}]
            }]
        }

        definition, sense = _get_definition_from_selection(entry, 0, 0)

        assert definition == "first sub"


class TestExtractExamples(unittest.TestCase):
    """Test extracting examples from sense."""

    def test_string_examples(self):
        """Test extracting string examples."""
        sense = {
            "examples": [
                "Example 1",
                "Example 2",
                "Example 3",
            ]
        }

        examples = _extract_examples(sense)

        assert examples == ["Example 1", "Example 2", "Example 3"]

    def test_dict_examples_with_text(self):
        """Test extracting dict examples with 'text' key."""
        sense = {
            "examples": [
                {"text": "Example 1"},
                {"text": "Example 2"},
            ]
        }

        examples = _extract_examples(sense)

        assert examples == ["Example 1", "Example 2"]

    def test_mixed_string_and_dict_examples(self):
        """Test mixed string and dict examples."""
        sense = {
            "examples": [
                "String example",
                {"text": "Dict example"},
            ]
        }

        examples = _extract_examples(sense)

        assert examples == ["String example", "Dict example"]

    def test_max_examples_limit(self):
        """Test examples are limited to max_examples."""
        sense = {
            "examples": [
                "Example 1",
                "Example 2",
                "Example 3",
                "Example 4",
            ]
        }

        examples = _extract_examples(sense, max_examples=2)

        assert len(examples) == 2
        assert examples == ["Example 1", "Example 2"]

    def test_no_examples_returns_none(self):
        """Test missing examples returns None."""
        sense = {}

        examples = _extract_examples(sense)

        assert examples is None

    def test_empty_examples_list_returns_none(self):
        """Test empty examples list returns None."""
        sense = {"examples": []}

        examples = _extract_examples(sense)

        assert examples is None

    def test_dict_examples_without_text_skipped(self):
        """Test dict examples without 'text' key are skipped."""
        sense = {
            "examples": [
                {"other_key": "value"},
                {"text": "Valid example"},
            ]
        }

        examples = _extract_examples(sense)

        assert examples == ["Valid example"]

    def test_max_examples_with_skipped_items(self):
        """Test max_examples limit with skipped invalid items."""
        sense = {
            "examples": [
                {"text": "Valid 1"},
                {"invalid": "dict"},
                {"text": "Valid 2"},
                "Valid 3",
            ]
        }

        examples = _extract_examples(sense, max_examples=2)

        # max_examples=2 slices the list first, then filters valid items
        # First 2 items: {"text": "Valid 1"}, {"invalid": "dict"} → only "Valid 1" is valid
        assert len(examples) == 1

    def test_default_max_examples_is_3(self):
        """Test default max_examples is 3."""
        sense = {
            "examples": [
                "Ex1", "Ex2", "Ex3", "Ex4", "Ex5"
            ]
        }

        examples = _extract_examples(sense)

        assert len(examples) == 3

    def test_empty_sense_handles_gracefully(self):
        """Test empty sense dict is handled gracefully."""
        examples = _extract_examples({})

        assert examples is None


class TestEdgeCases(unittest.IsolatedAsyncioTestCase):
    """Test edge cases and error conditions."""

    async def test_empty_word_and_sentence(self):
        """Test select_best_sense with empty word and sentence."""
        entries = [{"partOfSpeech": "noun", "senses": [{"definition": "def"}]}]

        result = await select_best_sense("", "", entries, FakeLLMAdapter())

        assert isinstance(result, SenseResult)

    def test_parse_response_with_floats(self):
        """Test parsing response with decimal points."""
        entries = [
            {"partOfSpeech": "noun", "senses": [{"definition": "1"}, {"definition": "2"}]},
        ]

        ei, si, ssi = _parse_sense_response("0.1", entries)

        assert (ei, si, ssi) == (0, 1, -1)

    def test_build_prompt_with_special_characters(self):
        """Test building prompt with special characters."""
        entries = [{
            "partOfSpeech": "noun",
            "senses": [{"definition": "def with \"quotes\" and 'apostrophes'"}]
        }]

        prompt = _build_sense_prompt("Test \"quote\" sentence", "word's", entries)

        # Should not crash
        assert "Test" in prompt
        assert "word" in prompt

    def test_get_definition_with_empty_entry(self):
        """Test _get_definition_from_selection with empty entry dict."""
        definition, sense = _get_definition_from_selection({}, 0, -1)

        assert definition == ""
        assert sense is None

    def test_extract_examples_with_large_example_list(self):
        """Test extracting examples from sense with many examples."""
        sense = {
            "examples": [f"Example {i}" for i in range(100)]
        }

        examples = _extract_examples(sense, max_examples=5)

        assert len(examples) == 5
        assert examples[0] == "Example 0"
        assert examples[4] == "Example 4"


class TestIntegrationScenarios(unittest.IsolatedAsyncioTestCase):
    """Test realistic integration scenarios."""

    async def test_full_sense_selection_flow(self):
        """Test complete sense selection flow."""
        entries = [
            {
                "partOfSpeech": "noun",
                "senses": [
                    {"definition": "the noun sense"},
                    {"definition": "second noun sense"},
                ]
            },
            {
                "partOfSpeech": "verb",
                "senses": [
                    {
                        "definition": "the verb sense",
                        "examples": ["Example 1", {"text": "Example 2"}]
                    }
                ]
            }
        ]

        stats = LLMCallResult(
            model="gpt-4", prompt_tokens=80, completion_tokens=2,
            total_tokens=82, estimated_cost=0.001
        )
        fake_llm = FakeLLMAdapter(response="1.0", stats=stats)

        result = await select_best_sense("Test sentence", "word", entries, fake_llm)

        assert result.entry_idx == 1
        assert result.sense_idx == 0
        assert result.definition == "the verb sense"
        assert result.examples == ["Example 1", "Example 2"]
        assert result.stats == stats

    async def test_subsense_selection_with_examples(self):
        """Test subsense selection with examples extraction."""
        entries = [{
            "partOfSpeech": "noun",
            "senses": [{
                "definition": "main definition",
                "examples": ["Main ex"],
                "subsenses": [
                    {"definition": "sub1", "examples": ["Sub ex 1"]},
                    {"definition": "sub2", "examples": ["Sub ex 2", "Sub ex 2b"]},
                ]
            }]
        }]

        stats = LLMCallResult(
            model="gpt-4", prompt_tokens=60, completion_tokens=2,
            total_tokens=62, estimated_cost=0.001
        )
        fake_llm = FakeLLMAdapter(response="0.0.1", stats=stats)

        result = await select_best_sense("Test", "word", entries, fake_llm)

        assert result.subsense_idx == 1
        assert result.definition == "sub2"
        # Examples come from the parent sense, not the subsense
        assert "Main ex" in (result.examples or [])


if __name__ == '__main__':
    unittest.main()
