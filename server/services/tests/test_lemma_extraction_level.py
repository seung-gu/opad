"""Tests that the CEFR level from the LLM is kept only when it is A1-C2."""

import asyncio

from adapter.outbound.fake.llm import FakeLLMAdapter
from services.lemma_extraction import extract_lemma


def _level_from_llm(response: str):
    llm = FakeLLMAdapter(response=response)
    result, _ = asyncio.run(extract_lemma("Hund", "Der Hund bellt.", "English", llm))
    return result["level"]


def test_valid_level_is_kept():
    assert _level_from_llm('{"lemma": "Hund", "level": "B1"}') == "B1"


def test_lowercase_and_spaces_are_cleaned():
    assert _level_from_llm('{"lemma": "Hund", "level": " b1 "}') == "B1"


def test_level_outside_a1_c2_becomes_none():
    assert _level_from_llm('{"lemma": "Hund", "level": "D1"}') is None


def test_missing_level_becomes_none():
    assert _level_from_llm('{"lemma": "Hund"}') is None
