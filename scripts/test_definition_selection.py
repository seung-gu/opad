"""Test definition selection methods: tag-based vs LLM-based.

Usage:
    PYTHONPATH=. uv run python scripts/test_definition_selection.py
"""

import asyncio
import time

import httpx
import litellm

API_URL = "https://freedictionaryapi.com/api/v1/entries"


async def get_senses(lemma: str, lang: str) -> list[dict]:
    """Fetch all senses from Free Dictionary API."""
    url = f"{API_URL}/{lang}/{lemma}"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        if r.status_code == 200:
            data = r.json()
            entries = data.get("entries", [])
            if entries:
                return entries[0].get("senses", [])
    return []


def select_by_tags(sentence: str, senses: list[dict]) -> int:
    """Select definition based on grammatical tags.

    Logic:
    - If sentence contains reflexive/dative pronouns (mir, dir, sich, etc.)
      → prefer definitions with 'reflexive' or 'dative' tags
    - Otherwise → return first definition
    """
    sentence_lower = sentence.lower()
    reflexive_pronouns = ["mir", "dir", "sich", "mich", "dich", "uns", "euch"]
    has_reflexive = any(p in sentence_lower for p in reflexive_pronouns)

    if has_reflexive:
        for i, sense in enumerate(senses):
            tags = sense.get("tags", [])
            if "reflexive" in tags or "dative" in tags:
                return i

    return 0  # Default: first definition


async def select_by_llm(lemma: str, sentence: str, senses: list[dict]) -> tuple[int, float]:
    """Select definition using LLM.

    Returns:
        tuple: (selected_index, elapsed_time)
    """
    # Build options list (limit to 6 for context length)
    options = []
    for i, sense in enumerate(senses[:6]):
        defn = sense.get("definition", "")
        options.append(f"{i+1}. {defn}")

    prompt = f"""Lemma: "{lemma}"
Sentence: "{sentence}"

Which definition best matches the usage in this sentence?
Reply with the number only.

{chr(10).join(options)}"""

    start = time.time()
    response = await litellm.acompletion(
        model="gemini/gemini-2.0-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        timeout=15
    )
    elapsed = time.time() - start

    try:
        selected = int(response.choices[0].message.content.strip()) - 1
        return selected, elapsed
    except ValueError:
        return 0, elapsed


# Test cases: (lemma, lang_code, sentence, expected_index, description)
TEST_CASES = [
    # vorstellen - 6 meanings
    ("vorstellen", "de", "Ich stelle mir vor, dass er morgen kommt.", 3, "to imagine"),
    ("vorstellen", "de", "Darf ich mich vorstellen?", 2, "introduce oneself"),
    ("vorstellen", "de", "Er stellte seinen Freund vor.", 1, "introduce someone"),

    # aufhören - 2 meanings
    ("aufhören", "de", "Er hört mit dem Rauchen auf.", 1, "to stop"),

    # ansehen - 5 meanings
    ("ansehen", "de", "Ich sehe mir den Film an.", 4, "to watch"),
    ("ansehen", "de", "Sie sieht ihn böse an.", 2, "look at with expression"),

    # ausgehen - multiple meanings
    ("ausgehen", "de", "Wir gehen heute Abend aus.", 1, "to go out"),

    # anfangen - basic
    ("anfangen", "de", "Das Spiel fängt um 8 an.", 1, "to begin"),
]


async def run_tests():
    """Run all tests and compare methods."""
    print("=" * 70)
    print("Definition Selection Test: Tag-based vs LLM-based")
    print("=" * 70)

    tag_correct = 0
    llm_correct = 0
    total_time = 0
    results = []

    for lemma, lang, sentence, expected_idx, description in TEST_CASES:
        print(f"\n--- {lemma}: {description} ---")
        print(f"Sentence: {sentence}")
        print(f"Expected: #{expected_idx}")

        # Fetch senses
        senses = await get_senses(lemma, lang)
        if not senses:
            print("  ⚠️  No senses found, skipping")
            continue

        # Show available senses
        print(f"Available senses ({len(senses)}):")
        for i, s in enumerate(senses[:6]):
            tags = s.get("tags", [])
            defn = s.get("definition", "")[:60]
            marker = "→" if i == expected_idx - 1 else " "
            print(f"  {marker} {i+1}. [{', '.join(tags[:3])}] {defn}...")

        # Tag-based selection
        tag_idx = select_by_tags(sentence, senses)
        tag_ok = tag_idx == expected_idx - 1
        if tag_ok:
            tag_correct += 1
        print(f"\nTag-based: #{tag_idx + 1} {'✅' if tag_ok else '❌'}")

        # LLM-based selection
        llm_idx, elapsed = await select_by_llm(lemma, sentence, senses)
        total_time += elapsed
        llm_ok = llm_idx == expected_idx - 1
        if llm_ok:
            llm_correct += 1
        print(f"LLM-based: #{llm_idx + 1} {'✅' if llm_ok else '❌'} ({elapsed:.2f}s)")

        results.append({
            "lemma": lemma,
            "expected": expected_idx,
            "tag": tag_idx + 1,
            "tag_ok": tag_ok,
            "llm": llm_idx + 1,
            "llm_ok": llm_ok,
            "time": elapsed
        })

    # Summary
    n = len(results)
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\n{'Method':<15} {'Correct':<10} {'Accuracy':<10} {'Avg Time':<10}")
    print("-" * 45)
    print(f"{'Tag-based':<15} {tag_correct}/{n:<8} {tag_correct/n*100:.0f}%{'':<7} {'0ms':<10}")
    print(f"{'LLM-based':<15} {llm_correct}/{n:<8} {llm_correct/n*100:.0f}%{'':<7} {total_time/n*1000:.0f}ms")

    print("\nDetailed Results:")
    print(f"{'Lemma':<12} {'Expected':<8} {'Tag':<8} {'LLM':<8}")
    print("-" * 40)
    for r in results:
        tag_mark = "✅" if r["tag_ok"] else f"❌{r['tag']}"
        llm_mark = "✅" if r["llm_ok"] else f"❌{r['llm']}"
        print(f"{r['lemma']:<12} {r['expected']:<8} {tag_mark:<8} {llm_mark:<8}")


if __name__ == "__main__":
    asyncio.run(run_tests())
