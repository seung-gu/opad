#!/usr/bin/env python3
"""Test script for token usage tracking with LiteLLM."""

import asyncio
import sys
sys.path.insert(0, "src")

from utils.llm import call_llm_with_tracking


async def test_token_usage():
    """Test token usage tracking with a simple prompt."""
    print("Testing token usage tracking...\n")

    # Test 1: Simple greeting
    print("=" * 50)
    print("Test 1: Simple greeting")
    print("=" * 50)

    content, stats = await call_llm_with_tracking(
        messages=[{"role": "user", "content": "Say hello in German"}],
        model="gpt-4.1-mini",
        max_tokens=50
    )

    print(f"Response: {content}")
    print(f"\nToken Usage:")
    print(f"  - Model: {stats.model}")
    print(f"  - Provider: {stats.provider}")
    print(f"  - Prompt tokens: {stats.prompt_tokens}")
    print(f"  - Completion tokens: {stats.completion_tokens}")
    print(f"  - Total tokens: {stats.total_tokens}")
    print(f"  - Estimated cost: ${stats.estimated_cost:.6f}")

    # Test 2: Dictionary-style query
    print("\n" + "=" * 50)
    print("Test 2: Dictionary-style query (like /dictionary/search)")
    print("=" * 50)

    prompt = """Define the German word "Geschäft" used in this sentence: "Das Geschäft ist heute geschlossen."

Return ONLY valid JSON:
{
  "lemma": "dictionary form",
  "definition": "meaning in Korean",
  "related_words": ["word1", "word2"],
  "pos": "noun/verb/adjective",
  "gender": "der/die/das (if noun)",
  "level": "A1/A2/B1/B2/C1/C2"
}"""

    content2, stats2 = await call_llm_with_tracking(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4.1-mini",
        max_tokens=200,
        temperature=0
    )

    print(f"Response: {content2[:200]}...")
    print(f"\nToken Usage:")
    print(f"  - Model: {stats2.model}")
    print(f"  - Provider: {stats2.provider}")
    print(f"  - Prompt tokens: {stats2.prompt_tokens}")
    print(f"  - Completion tokens: {stats2.completion_tokens}")
    print(f"  - Total tokens: {stats2.total_tokens}")
    print(f"  - Estimated cost: ${stats2.estimated_cost:.6f}")

    # Summary
    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    total_tokens = stats.total_tokens + stats2.total_tokens
    total_cost = stats.estimated_cost + stats2.estimated_cost
    print(f"Total tokens used: {total_tokens}")
    print(f"Total estimated cost: ${total_cost:.6f}")


if __name__ == "__main__":
    asyncio.run(test_token_usage())
