"""Tests for lemma extraction module — Step 1 of dictionary lookup pipeline.

Tests cover:
1. extract_lemma() dispatching: German → Stanza, other → LLM
2. _extract_with_stanza() with mocked Stanza pipeline
3. _find_target_token() — exact match and case-insensitive fallback
4. _build_lemma_from_dep_tree() — separable verbs, reflexive verbs, articles, adjectives
5. _estimate_cefr() — LLM call for CEFR level
6. _extract_with_llm() — LLM reduced prompt path
7. _build_reduced_prompt() — dispatches to de/en/generic
8. preload_stanza() — calls _get_stanza_pipeline
9. Error handling for each path
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch, call
import logging

import pytest

from utils.lemma_extraction import (
    extract_lemma,
    _extract_with_stanza,
    _find_target_token,
    _build_lemma_from_dep_tree,
    _estimate_cefr,
    _extract_with_llm,
    _build_reduced_prompt,
    _build_reduced_prompt_de,
    _build_reduced_prompt_en,
    _build_reduced_prompt_generic,
    preload_stanza,
    _get_stanza_pipeline,
)
from adapter.fake.llm import FakeLLMAdapter
from domain.model.token_usage import LLMCallResult


class TestExtractLemmaDispatching(unittest.IsolatedAsyncioTestCase):
    """Test extract_lemma() language dispatching."""

    @patch('utils.lemma_extraction._extract_with_stanza')
    @patch('utils.lemma_extraction._estimate_cefr')
    async def test_german_uses_stanza_path(self, mock_cefr, mock_stanza):
        """Test German language uses Stanza extraction."""
        mock_stanza.return_value = {
            "lemma": "singen",
            "related_words": ["singt"]
        }
        stats = LLMCallResult(
            model="gpt-4", prompt_tokens=10, completion_tokens=2,
            total_tokens=12, estimated_cost=0.0001
        )
        mock_cefr.return_value = ("A1", stats)

        result, returned_stats = await extract_lemma(
            "singt", "Er singt unter der Dusche", "German", FakeLLMAdapter()
        )

        assert result is not None
        assert result["lemma"] == "singen"
        assert result["level"] == "A1"
        mock_stanza.assert_called_once_with("singt", "Er singt unter der Dusche")
        mock_cefr.assert_called_once()

    @patch('utils.lemma_extraction._extract_with_llm')
    async def test_english_uses_llm_path(self, mock_llm):
        """Test English language uses LLM extraction."""
        stats = LLMCallResult(
            model="gpt-4", prompt_tokens=50, completion_tokens=5,
            total_tokens=55, estimated_cost=0.001
        )
        mock_llm.return_value = ({
            "lemma": "sing",
            "related_words": ["sang"],
            "level": "A1"
        }, stats)

        result, returned_stats = await extract_lemma(
            "sang", "She sang beautifully", "English", FakeLLMAdapter()
        )

        assert result is not None
        assert result["lemma"] == "sing"
        mock_llm.assert_called_once()

    @patch('utils.lemma_extraction._extract_with_stanza')
    @patch('utils.lemma_extraction._extract_with_llm')
    async def test_stanza_failure_falls_back_to_llm(self, mock_llm, mock_stanza):
        """Test fallback to LLM when Stanza fails."""
        mock_stanza.return_value = None
        stats = LLMCallResult(
            model="gpt-4", prompt_tokens=50, completion_tokens=5,
            total_tokens=55, estimated_cost=0.001
        )
        mock_llm.return_value = ({
            "lemma": "singen",
            "related_words": ["singt"],
            "level": "A1"
        }, stats)

        result, returned_stats = await extract_lemma(
            "singt", "Er singt", "German", FakeLLMAdapter()
        )

        assert result is not None
        mock_stanza.assert_called_once()
        mock_llm.assert_called_once()

    @patch('utils.lemma_extraction._extract_with_llm')
    async def test_french_uses_llm_path(self, mock_llm):
        """Test other languages (French) use LLM."""
        stats = LLMCallResult(
            model="gpt-4", prompt_tokens=50, completion_tokens=5,
            total_tokens=55, estimated_cost=0.001
        )
        mock_llm.return_value = ({
            "lemma": "chanter",
            "related_words": ["chante"],
            "level": "A1"
        }, stats)

        result, returned_stats = await extract_lemma(
            "chante", "Elle chante", "French", FakeLLMAdapter()
        )

        assert result is not None
        mock_llm.assert_called_once()

    @patch('utils.lemma_extraction._extract_with_stanza')
    @patch('utils.lemma_extraction._estimate_cefr')
    async def test_both_stanza_and_cefr_return_none_on_exception(self, mock_cefr, mock_stanza):
        """Test returns (None, None) when Stanza extraction succeeds but CEFR fails and both fail."""
        mock_stanza.return_value = None

        with patch('utils.lemma_extraction._extract_with_llm') as mock_llm:
            mock_llm.return_value = (None, None)

            result, stats = await extract_lemma(
                "xyz", "test xyz", "German", FakeLLMAdapter()
            )

            assert result is None
            assert stats is None


class TestExtractWithStanza(unittest.IsolatedAsyncioTestCase):
    """Test Stanza-based extraction."""

    async def test_stanza_basic_verb_extraction(self):
        """Test basic verb lemma extraction with Stanza."""
        mock_token = MagicMock()
        mock_token.text = "singt"
        mock_token.lemma = "singen"
        mock_token.upos = "VERB"
        mock_token.id = 2
        mock_token.head = 0
        mock_token.xpos = "VVFIN"

        mock_sent = MagicMock()
        mock_sent.words = [mock_token]

        mock_doc = MagicMock()
        mock_doc.sentences = [mock_sent]

        with patch('utils.lemma_extraction._get_stanza_pipeline') as mock_pipeline:
            mock_pipeline.return_value = MagicMock(return_value=mock_doc)

            result = await _extract_with_stanza("singt", "Er singt")

        assert result is not None
        assert result["lemma"] == "singen"
        assert result["related_words"] == ["singt"]

    async def test_stanza_extraction_pipeline_error(self):
        """Test Stanza extraction returns None on pipeline error."""
        with patch('utils.lemma_extraction._get_stanza_pipeline') as mock_pipeline:
            mock_pipeline.side_effect = Exception("Pipeline error")

            result = await _extract_with_stanza("singt", "Er singt")

        assert result is None

    async def test_stanza_extraction_no_target_token(self):
        """Test Stanza extraction returns None when target token not found."""
        mock_sent = MagicMock()
        mock_sent.words = []

        mock_doc = MagicMock()
        mock_doc.sentences = [mock_sent]

        with patch('utils.lemma_extraction._get_stanza_pipeline') as mock_pipeline:
            mock_pipeline.return_value = MagicMock(return_value=mock_doc)

            result = await _extract_with_stanza("nothere", "Er singt")

        assert result is None


class TestFindTargetToken(unittest.TestCase):
    """Test finding target token in Stanza document."""

    def test_exact_match_finds_token(self):
        """Test exact match returns correct token."""
        mock_token = MagicMock()
        mock_token.text = "singt"

        mock_sent = MagicMock()
        mock_sent.words = [mock_token]

        mock_doc = MagicMock()
        mock_doc.sentences = [mock_sent]

        token, sent = _find_target_token(mock_doc, "singt")
        assert token == mock_token
        assert sent == mock_sent

    def test_case_insensitive_fallback(self):
        """Test case-insensitive fallback when exact match fails."""
        mock_token = MagicMock()
        mock_token.text = "Singt"

        mock_sent = MagicMock()
        mock_sent.words = [mock_token]

        mock_doc = MagicMock()
        mock_doc.sentences = [mock_sent]

        token, sent = _find_target_token(mock_doc, "singt")
        assert token == mock_token
        assert sent == mock_sent

    def test_no_match_returns_none(self):
        """Test returns None when no match found."""
        mock_token = MagicMock()
        mock_token.text = "singt"

        mock_sent = MagicMock()
        mock_sent.words = [mock_token]

        mock_doc = MagicMock()
        mock_doc.sentences = [mock_sent]

        token, sent = _find_target_token(mock_doc, "andere")
        assert token is None
        assert sent is None

    def test_multiple_sentences(self):
        """Test finding token in multiple sentences."""
        mock_token_1 = MagicMock()
        mock_token_1.text = "hello"

        mock_token_2 = MagicMock()
        mock_token_2.text = "singt"

        mock_sent_1 = MagicMock()
        mock_sent_1.words = [mock_token_1]

        mock_sent_2 = MagicMock()
        mock_sent_2.words = [mock_token_2]

        mock_doc = MagicMock()
        mock_doc.sentences = [mock_sent_1, mock_sent_2]

        token, sent = _find_target_token(mock_doc, "singt")
        assert token == mock_token_2
        assert sent == mock_sent_2


class TestBuildLemmaFromDepTree(unittest.TestCase):
    """Test building lemma from Stanza dependency tree."""

    def test_simple_verb_extraction(self):
        """Test simple verb (no prefix, no reflexive)."""
        target = MagicMock()
        target.id = 2
        target.text = "singt"
        target.lemma = "singen"
        target.upos = "VERB"
        target.xpos = "VVFIN"

        mock_sent = MagicMock()
        mock_sent.words = [target]

        mock_doc = MagicMock()
        mock_doc.sentences = [mock_sent]

        lemma, related_words = _build_lemma_from_dep_tree(mock_sent, target,"singt")

        assert lemma == "singen"
        assert related_words == ["singt"]

    def test_separable_verb_extraction(self):
        """Test separable verb with prefix (compound:prt)."""
        target = MagicMock()
        target.id = 2
        target.text = "macht"
        target.lemma = "machen"
        target.upos = "VERB"
        target.xpos = "VVFIN"

        prefix = MagicMock()
        prefix.id = 3
        prefix.text = "zu"
        prefix.head = 2
        prefix.deprel = "compound:prt"

        mock_sent = MagicMock()
        mock_sent.words = [target, prefix]

        mock_doc = MagicMock()
        mock_doc.sentences = [mock_sent]

        lemma, related_words = _build_lemma_from_dep_tree(mock_sent, target,"macht")

        assert lemma == "zumachen"
        assert set(related_words) == {"macht", "zu"}

    def test_reflexive_verb_extraction(self):
        """Test reflexive verb with sich."""
        target = MagicMock()
        target.id = 2
        target.text = "beschäftigt"
        target.lemma = "beschäftigen"
        target.upos = "VERB"
        target.xpos = "VVFIN"

        reflexive = MagicMock()
        reflexive.id = 1
        reflexive.text = "sich"
        reflexive.head = 2
        reflexive.xpos = "PRF"

        mock_sent = MagicMock()
        mock_sent.words = [reflexive, target]

        mock_doc = MagicMock()
        mock_doc.sentences = [mock_sent]

        lemma, related_words = _build_lemma_from_dep_tree(mock_sent, target,"beschäftigt")

        assert lemma == "sich beschäftigen"
        assert set(related_words) == {"beschäftigt", "sich"}

    def test_reflexive_separable_verb_extraction(self):
        """Test reflexive + separable verb: sich + prefix + verb."""
        target = MagicMock()
        target.id = 3
        target.text = "bereitet"
        target.lemma = "bereiten"
        target.upos = "VERB"
        target.xpos = "VVFIN"

        reflexive = MagicMock()
        reflexive.id = 1
        reflexive.text = "sich"
        reflexive.head = 3
        reflexive.xpos = "PRF"

        prefix = MagicMock()
        prefix.id = 4
        prefix.text = "vor"
        prefix.head = 3
        prefix.deprel = "compound:prt"

        mock_sent = MagicMock()
        mock_sent.words = [reflexive, target, prefix]

        mock_doc = MagicMock()
        mock_doc.sentences = [mock_sent]

        lemma, related_words = _build_lemma_from_dep_tree(mock_sent, target,"bereitet")

        assert lemma == "sich vorbereiten"
        assert set(related_words) == {"bereitet", "sich", "vor"}

    def test_article_handling(self):
        """Test article lemma returns text.lower()."""
        target = MagicMock()
        target.id = 1
        target.text = "Der"
        target.lemma = "der"
        target.upos = "DET"
        target.xpos = "ART"

        mock_sent = MagicMock()
        mock_sent.words = [target]

        mock_doc = MagicMock()
        mock_doc.sentences = [mock_sent]

        lemma, related_words = _build_lemma_from_dep_tree(mock_sent, target,"Der")

        assert lemma == "der"
        assert related_words == ["Der"]

    def test_past_participle_adjective_handling(self):
        """Test past-participle used as adjective."""
        target = MagicMock()
        target.id = 1
        target.text = "aufgeregt"
        target.lemma = "aufregten"  # Ends in 'en'
        target.upos = "ADJ"
        target.xpos = "ADJA"

        mock_sent = MagicMock()
        mock_sent.words = [target]

        mock_doc = MagicMock()
        mock_doc.sentences = [mock_sent]

        lemma, related_words = _build_lemma_from_dep_tree(mock_sent, target,"aufgeregt")

        assert lemma == "aufgeregt"
        assert related_words == ["aufgeregt"]

    def test_non_verb_extraction(self):
        """Test non-verb returns lemma as-is."""
        target = MagicMock()
        target.id = 1
        target.text = "Hund"
        target.lemma = "Hund"
        target.upos = "NOUN"
        target.xpos = "NN"

        mock_sent = MagicMock()
        mock_sent.words = [target]

        mock_doc = MagicMock()
        mock_doc.sentences = [mock_sent]

        lemma, related_words = _build_lemma_from_dep_tree(mock_sent, target,"Hund")

        assert lemma == "Hund"
        assert related_words == ["Hund"]

    def test_related_words_sorted_by_position(self):
        """Test related_words are sorted by token id position."""
        verb = MagicMock()
        verb.id = 3
        verb.text = "vorbereitet"
        verb.lemma = "vorbereiten"
        verb.upos = "VERB"
        verb.xpos = "VVFIN"

        prefix = MagicMock()
        prefix.id = 4
        prefix.text = "vor"
        prefix.head = 3
        prefix.deprel = "compound:prt"

        reflexive = MagicMock()
        reflexive.id = 1
        reflexive.text = "sich"
        reflexive.head = 3
        reflexive.xpos = "PRF"

        mock_sent = MagicMock()
        mock_sent.words = [reflexive, verb, prefix]

        mock_doc = MagicMock()
        mock_doc.sentences = [mock_sent]

        lemma, related_words = _build_lemma_from_dep_tree(mock_sent, verb, "vorbereitet")

        # Should be sorted by id: 1 (sich), 3 (vorbereitet), 4 (vor)
        assert related_words == ["sich", "vorbereitet", "vor"]


class TestEstimateCefr(unittest.IsolatedAsyncioTestCase):
    """Test CEFR estimation with LLM."""

    async def test_cefr_estimation_success(self):
        """Test successful CEFR estimation."""
        stats = LLMCallResult(
            model="gpt-4", prompt_tokens=20, completion_tokens=2,
            total_tokens=22, estimated_cost=0.00005
        )
        fake_llm = FakeLLMAdapter(response='{"level": "B1"}', stats=stats)

        level, returned_stats = await _estimate_cefr(
            "beschäftigt", "Er beschäftigt sich", "beschäftigen", fake_llm, "gpt-4"
        )

        assert level == "B1"
        assert returned_stats == stats

    async def test_cefr_estimation_invalid_json(self):
        """Test CEFR estimation with invalid JSON response."""
        stats = LLMCallResult(
            model="gpt-4", prompt_tokens=20, completion_tokens=2,
            total_tokens=22, estimated_cost=0.00005
        )
        fake_llm = FakeLLMAdapter(response='invalid json', stats=stats)

        level, returned_stats = await _estimate_cefr(
            "word", "sentence", "lemma", fake_llm, "gpt-4"
        )

        assert level is None
        # Stats are still returned even when JSON parse fails
        assert returned_stats is not None

    async def test_cefr_estimation_api_error(self):
        """Test CEFR estimation returns None on API error."""
        failing_llm = MagicMock()
        failing_llm.call = AsyncMock(side_effect=Exception("API error"))

        level, returned_stats = await _estimate_cefr(
            "word", "sentence", "lemma", failing_llm, "gpt-4"
        )

        assert level is None
        assert returned_stats is None


class TestExtractWithLlm(unittest.IsolatedAsyncioTestCase):
    """Test LLM-based lemma extraction."""

    async def test_llm_extraction_success(self):
        """Test successful LLM-based extraction."""
        stats = LLMCallResult(
            model="gpt-4", prompt_tokens=50, completion_tokens=5,
            total_tokens=55, estimated_cost=0.001
        )
        fake_llm = FakeLLMAdapter(
            response='{"lemma": "sing", "related_words": ["sang"], "level": "A1"}',
            stats=stats,
        )

        result, returned_stats = await _extract_with_llm(
            "sang", "She sang", "English", fake_llm, "gpt-4"
        )

        assert result is not None
        assert result["lemma"] == "sing"
        assert result["related_words"] == ["sang"]
        assert result["level"] == "A1"
        assert returned_stats == stats

    async def test_llm_extraction_invalid_json(self):
        """Test LLM extraction with invalid JSON response."""
        stats = LLMCallResult(
            model="gpt-4", prompt_tokens=50, completion_tokens=5,
            total_tokens=55, estimated_cost=0.001
        )
        fake_llm = FakeLLMAdapter(response="This is not JSON", stats=stats)

        result, returned_stats = await _extract_with_llm(
            "word", "sentence", "English", fake_llm, "gpt-4"
        )

        assert result is None

    async def test_llm_extraction_api_error(self):
        """Test LLM extraction returns None on API error."""
        failing_llm = MagicMock()
        failing_llm.call = AsyncMock(side_effect=Exception("API error"))

        result, returned_stats = await _extract_with_llm(
            "word", "sentence", "English", failing_llm, "gpt-4"
        )

        assert result is None
        assert returned_stats is None


class TestBuildReducedPromptDispatching(unittest.TestCase):
    """Test reduced prompt building with language dispatch."""

    def test_english_prompt_dispatch(self):
        """Test English prompt is dispatched correctly."""
        prompt = _build_reduced_prompt("English", "She sang", "sang")
        assert "phrasal verb" in prompt.lower()
        assert "base form" in prompt.lower()

    def test_german_prompt_dispatch(self):
        """Test German prompt is dispatched correctly."""
        prompt = _build_reduced_prompt("German", "Er singt", "singt")
        assert "separable" in prompt.lower() or "lemma" in prompt.lower()

    def test_generic_prompt_dispatch(self):
        """Test generic prompt is used for other languages."""
        prompt = _build_reduced_prompt("French", "Elle chante", "chante")
        assert "separable verb" in prompt.lower() or "compound word" in prompt.lower()

    def test_german_prompt_contains_examples(self):
        """Test German prompt includes German-specific examples."""
        prompt = _build_reduced_prompt_de("Er singt", "singt")
        assert "singen" in prompt
        assert "zumachen" in prompt

    def test_english_prompt_contains_examples(self):
        """Test English prompt includes English-specific examples."""
        prompt = _build_reduced_prompt_en("She sang", "sang")
        assert "give up" in prompt
        assert "pick up" in prompt

    def test_generic_prompt_is_generic(self):
        """Test generic prompt doesn't mention specific languages."""
        prompt = _build_reduced_prompt_generic("French", "Elle chante", "chante")
        assert "separable" in prompt.lower() or "compound" in prompt.lower()

    def test_reduced_prompt_includes_sentence_and_word(self):
        """Test all prompts include the sentence and word."""
        for language, sentence, word in [
            ("German", "Er singt", "singt"),
            ("English", "She sang", "sang"),
            ("French", "Elle chante", "chante"),
        ]:
            prompt = _build_reduced_prompt(language, sentence, word)
            assert sentence in prompt
            assert word in prompt


class TestPreloadStanza(unittest.TestCase):
    """Test Stanza preloading."""

    @patch('utils.lemma_extraction._get_stanza_pipeline')
    def test_preload_stanza_calls_pipeline(self, mock_get_pipeline):
        """Test preload_stanza calls _get_stanza_pipeline."""
        mock_pipeline = MagicMock()
        mock_get_pipeline.return_value = mock_pipeline

        preload_stanza()

        mock_get_pipeline.assert_called_once()

    @patch('utils.lemma_extraction._get_stanza_pipeline')
    def test_preload_is_idempotent(self, mock_get_pipeline):
        """Test preload_stanza can be called multiple times safely."""
        preload_stanza()
        preload_stanza()
        assert mock_get_pipeline.call_count == 2


class TestEdgeCases(unittest.IsolatedAsyncioTestCase):
    """Test edge cases and error conditions."""

    async def test_extract_lemma_with_empty_word(self):
        """Test extract_lemma with empty word string."""
        result, stats = await extract_lemma("", "test sentence", "German", FakeLLMAdapter())
        # Should not crash, may return None or empty result

    async def test_extract_lemma_with_empty_sentence(self):
        """Test extract_lemma with empty sentence."""
        result, stats = await extract_lemma("word", "", "German", FakeLLMAdapter())
        # Should not crash

    @patch('utils.lemma_extraction._extract_with_stanza')
    @patch('utils.lemma_extraction._estimate_cefr')
    async def test_extract_lemma_cefr_none_level(self, mock_cefr, mock_stanza):
        """Test extract_lemma when CEFR returns None level."""
        mock_stanza.return_value = {
            "lemma": "singen",
            "related_words": ["singt"]
        }
        stats = LLMCallResult(
            model="gpt-4", prompt_tokens=10, completion_tokens=2,
            total_tokens=12, estimated_cost=0.0001
        )
        mock_cefr.return_value = (None, stats)

        result, returned_stats = await extract_lemma(
            "singt", "Er singt", "German", FakeLLMAdapter()
        )

        assert result is not None
        assert result["level"] is None
        assert returned_stats is not None

    def test_find_target_token_empty_document(self):
        """Test finding token in empty document."""
        mock_doc = MagicMock()
        mock_doc.sentences = []

        token, sent = _find_target_token(mock_doc, "word")
        assert token is None
        assert sent is None

    def test_build_lemma_no_related_parts_defaults_to_word(self):
        """Test that when no related parts found, falls back to [word]."""
        target = MagicMock()
        target.id = 1
        target.text = "Hund"
        target.lemma = "Hund"
        target.upos = "NOUN"
        target.xpos = "NN"

        # Create separate word not linked to target
        other = MagicMock()
        other.id = 2
        other.text = "run"
        other.head = 0

        mock_sent = MagicMock()
        mock_sent.words = [target, other]

        mock_doc = MagicMock()
        mock_doc.sentences = [mock_sent]

        lemma, related_words = _build_lemma_from_dep_tree(mock_sent, target,"Hund")

        assert related_words == ["Hund"]


class TestIntegrationScenarios(unittest.IsolatedAsyncioTestCase):
    """Test realistic integration scenarios."""

    @patch('utils.lemma_extraction._extract_with_stanza')
    @patch('utils.lemma_extraction._estimate_cefr')
    async def test_german_reflexive_verb_full_flow(self, mock_cefr, mock_stanza):
        """Test complete German reflexive verb flow."""
        mock_stanza.return_value = {
            "lemma": "sich langweilen",
            "related_words": ["sich", "langweilt"]
        }
        stats = LLMCallResult(
            model="gpt-4", prompt_tokens=15, completion_tokens=2,
            total_tokens=17, estimated_cost=0.0001
        )
        mock_cefr.return_value = ("B1", stats)

        result, returned_stats = await extract_lemma(
            "langweilt", "Ich glaube, dass er sich langweilt", "German", FakeLLMAdapter()
        )

        assert result is not None
        assert result["lemma"] == "sich langweilen"
        assert set(result["related_words"]) == {"sich", "langweilt"}
        assert result["level"] == "B1"

    @patch('utils.lemma_extraction._extract_with_stanza')
    @patch('utils.lemma_extraction._estimate_cefr')
    async def test_german_separable_verb_full_flow(self, mock_cefr, mock_stanza):
        """Test complete German separable verb flow."""
        mock_stanza.return_value = {
            "lemma": "zumachen",
            "related_words": ["macht", "zu"]
        }
        stats = LLMCallResult(
            model="gpt-4", prompt_tokens=15, completion_tokens=2,
            total_tokens=17, estimated_cost=0.0001
        )
        mock_cefr.return_value = ("A2", stats)

        result, returned_stats = await extract_lemma(
            "macht", "Der Laden macht um 18 Uhr zu", "German", FakeLLMAdapter()
        )

        assert result is not None
        assert result["lemma"] == "zumachen"
        assert set(result["related_words"]) == {"macht", "zu"}
        assert result["level"] == "A2"


if __name__ == '__main__':
    unittest.main()
