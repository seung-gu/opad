"""Test reduced prompt for lemma extraction accuracy.

Usage:
    PYTHONPATH=. uv run python scripts/test_reduced_prompt.py
    PYTHONPATH=. uv run python scripts/test_reduced_prompt.py --model openai/gpt-4.1-mini
    PYTHONPATH=. uv run python scripts/test_reduced_prompt.py --model gemini/gemini-2.0-flash
"""

import argparse
import asyncio
import json
import random
import time

import litellm

from utils.prompts import build_reduced_word_definition_prompt
from scripts.test_cases import TEST_CASES_DE, TEST_CASES_EN


def build_test_prompt(language: str, sentence: str, word: str) -> str:
    """Build test prompt for lemma extraction based on language."""

    if language == "English":
        return build_test_prompt_en(sentence, word)
    else:
        return build_test_prompt_de(sentence, word)


def build_test_prompt_de(sentence: str, word: str) -> str:
    """German test prompt."""
    return f"""Sentence: "{sentence}"
Word: "{word}"

lemma = dictionary lemma of "{word}".
    - Verbs: infinitive 
        1. SEPARABLE: What is the LAST word of "{sentence}" (before punctuation)?
            If it's: ab/an/auf/aus/bei/ein/mit/nach/vor/weg/zu/zurück/teil/statt/unter/über/um)? → combine with verb
        2. REFLEXIVE: Does any reflexive pronoun (sich/mich/dich/uns/euch) appear with the verb? → add "sich " to lemma
    - Nouns: singular nominative without article
    - Other (articles, adverbs, pronouns, particles): lowercase, as-is

related_words = exact words from sentence forming this {{lemma}}, sorted by position in "{sentence}" (left → right)
    - Verbs: collect ONLY conjugated verb + reflexive pronoun (sich/mich/dich/uns/euch) + separable prefix. Nothing else.
      EXCLUDE: subjects, modals (kann/muss/will/soll/darf/möchte/sollte/sollten/müsst/könnte/wollte), auxiliaries (hat/ist/war/wurde/haben/sein/werden).
      Past participles (ge- forms like angefangen/ausgemacht): include ONLY the participle, never hat/ist/wurde.
    - Non-verbs (nouns, adjectives, adverbs, prepositions, articles, conjunctions): ["{word}"]
level (CEFR) = A1(basic) A2(daily) B1(general) B2(professional) C1(academic) C2(literary)

Respond with JSON only, no explanation:
{{"lemma": "...", "related_words": [...], "level": "..."}}

example:
Sentence: "Er singt unter der Dusche", Word: "singt"
→ {{"lemma": "singen", "related_words": ["singt"], "level": "A1"}}

Sentence: "Der Laden macht um 18 Uhr zu", Word: "macht"
→ {{"lemma": "zumachen", "related_words": ["macht", "zu"], "level": "A2"}}

Sentence: "Er beschäftigt sich mit Geschichte", Word: "beschäftigt"
→ {{"lemma": "sich beschäftigen", "related_words": ["beschäftigt", "sich"], "level": "B1"}}

Sentence: "Sie bereitet sich auf die Prüfung vor", Word: "bereitet"
→ {{"lemma": "sich vorbereiten", "related_words": ["bereitet", "sich", "vor"], "level": "B1"}}

Sentence: "Ich glaube, dass er sich langweilt", Word: "langweilt"
→ {{"lemma": "sich langweilen", "related_words": ["sich", "langweilt"], "level": "B1"}}

Sentence: "Sie kann sich nicht entschließen", Word: "entschließen"
→ {{"lemma": "sich entschließen", "related_words": ["sich", "entschließen"], "level": "B2"}}

Sentence: "Wir dürfen uns nicht verspäten", Word: "verspäten"
→ {{"lemma": "sich verspäten", "related_words": ["uns", "verspäten"], "level": "B1"}}

Sentence: "Sie hat die Tür zugemacht", Word: "zugemacht"
→ {{"lemma": "zumachen", "related_words": ["zugemacht"], "level": "A2"}}

Sentence: "Er ist nach Berlin abgereist", Word: "abgereist"
→ {{"lemma": "abreisen", "related_words": ["abgereist"], "level": "B1"}}

"""


def build_test_prompt_en(sentence: str, word: str) -> str:
    """English test prompt."""
    return f"""Sentence: "{sentence}"
Word: "{word}"

Return the English dictionary lemma of "{word}".
- Verbs: base form (infinitive without "to")
    1. PHRASAL VERB: What is the word after "{word}" OR after the object of "{word}"?
        If it's: up/down/off/on/out/in/away/back/over/through
        → combine verb + particle as lemma (e.g., "give up", "turn off")
    2. IRREGULAR: Return base form (went→go, written→write)
- Nouns: singular form (children→child)
- Adjectives: positive form (better→good)
- If "{word}" IS the particle → find its verb and combine (e.g., "up" in "gave up" → "give up")
- Other (adverbs, prepositions, conjunctions): as-is

related_words = exact words from sentence forming this lemma (always includes "{word}")
level (CEFR) = A1(basic) A2(daily) B1(general) B2(professional) C1(academic) C2(literary)

Respond with JSON only, no explanation:
{{"lemma": "...", "related_words": ["{word}", ...], "level": "..."}}

Examples:
Sentence: "She gave up smoking", Word: "gave"
→ {{"lemma": "give up", "related_words": ["gave", "up"], "level": "B1"}}

Sentence: "She picked her keys up from the table", Word: "picked"
→ {{"lemma": "pick up", "related_words": ["picked", "up"], "level": "A2"}}

Sentence: "She picked her keys up from the table", Word: "up"
→ {{"lemma": "pick up", "related_words": ["picked", "up"], "level": "A2"}}

Sentence: "I saw the movie yesterday", Word: "saw"
→ {{"lemma": "see", "related_words": ["saw"], "level": "A1"}}

"""

# Use German test cases by default (imported from test_cases.py)
TEST_CASES = TEST_CASES_DE


async def test_single(model: str, sentence: str, word: str, expected_lemma: str, expected_rw: list[str], use_test_prompt: bool = False, language: str = "German") -> dict:
    """Test a single case and return result."""
    if use_test_prompt:
        prompt = build_test_prompt(language, sentence, word)
    else:
        prompt = build_reduced_word_definition_prompt(language, sentence, word)

    start_time = time.time()
    try:
        response = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            timeout=20
        )
        elapsed = time.time() - start_time

        content = response.choices[0].message.content

        # Parse JSON (handle markdown code blocks)
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        result = json.loads(content.strip())
        lemma = result.get("lemma", "")
        rw = result.get("related_words", [])

        # Evaluate
        lemma_ok = lemma == expected_lemma

        # Check related_words: both content AND order must match
        rw_lower = [r.lower() for r in rw]
        expected_rw_lower = [r.lower() for r in expected_rw]
        rw_ok = rw_lower == expected_rw_lower

        # Also track if content is correct but order is wrong
        rw_set_ok = set(rw_lower) == set(expected_rw_lower)
        rw_order_ok = rw_lower == expected_rw_lower

        return {
            "success": lemma_ok and rw_ok,
            "lemma_ok": lemma_ok,
            "rw_ok": rw_ok,
            "rw_set_ok": rw_set_ok,  # content correct (ignoring order)
            "rw_order_ok": rw_order_ok,  # order also correct
            "lemma": lemma,
            "rw": rw,
            "error": None,
            "time_ms": int(elapsed * 1000)
        }

    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "success": False,
            "lemma_ok": False,
            "rw_ok": False,
            "lemma": None,
            "rw": None,
            "error": str(e)[:50],
            "time_ms": int(elapsed * 1000)
        }


async def run_tests(model: str, delay: float = 0.5, use_test_prompt: bool = False, sample_pct: int = 100, test_cases_input: list = None, language: str = "German", start_index: int = 0, end_index: int = None):
    """Run all tests and print results."""
    all_cases = test_cases_input or TEST_CASES

    # Apply index range
    if start_index > 0 or end_index is not None:
        all_cases = all_cases[start_index:end_index]
        label = f"[{start_index}:{end_index or 'end'}]"
        print(f"Testing range {label} ({len(all_cases)} cases)")

    # Sample test cases if needed
    if sample_pct < 100:
        sample_size = max(1, int(len(all_cases) * sample_pct / 100))
        test_cases = random.sample(all_cases, sample_size)
        print(f"=" * 80)
        print(f"Testing: {model} [{language}] (sampling {sample_pct}% = {sample_size}/{len(all_cases)} cases)")
        print(f"=" * 80)
    else:
        test_cases = all_cases
        print(f"=" * 80)
        print(f"Testing: {model} [{language}]" + (" (TEST PROMPT)" if use_test_prompt else ""))
        print(f"=" * 80)

    results_by_category = {}
    total_passed = 0
    total_lemma_ok = 0
    total_rw_ok = 0
    total_rw_order_wrong = 0  # content correct but order wrong
    times_ms = []

    for sentence, word, exp_lemma, exp_rw, category in test_cases:
        result = await test_single(model, sentence, word, exp_lemma, exp_rw, use_test_prompt, language)
        times_ms.append(result.get("time_ms", 0))

        # Track by category
        if category not in results_by_category:
            results_by_category[category] = {"passed": 0, "total": 0}
        results_by_category[category]["total"] += 1

        ms = result['time_ms']
        if result["success"]:
            total_passed += 1
            results_by_category[category]["passed"] += 1
            print(f"✅ {word:15} → {result['lemma']:25} {ms}ms")
        else:
            if result["error"]:
                print(f"❌ {word:15} → ERROR: {result['error']}")
            else:
                got_l = result['lemma'] or '(none)'
                got_r = result['rw'] or []

                # Check if only order is wrong
                if result["lemma_ok"] and result.get("rw_set_ok") and not result.get("rw_order_ok"):
                    total_rw_order_wrong += 1
                    print(f"⚠️  {word:15} → rw ORDER wrong: {got_r}")
                    print(f"   {'':15}    expected order: {exp_rw}")
                elif not result["lemma_ok"] and not result["rw_ok"]:
                    print(f"❌ {word:15} → got: {got_l}, {got_r}")
                    print(f"   {'':15}    exp: {exp_lemma}, {exp_rw}")
                elif not result["lemma_ok"]:
                    print(f"❌ {word:15} → lemma: '{got_l}' (exp: '{exp_lemma}')")
                else:
                    print(f"❌ {word:15} → rw: {got_r} (exp: {exp_rw})")
                print(f"   {'':15}    sentence: {sentence}")

        if result["lemma_ok"]:
            total_lemma_ok += 1
        if result["rw_ok"]:
            total_rw_ok += 1

        await asyncio.sleep(delay)

    # Summary
    total = len(test_cases)
    avg_time = sum(times_ms) / len(times_ms) if times_ms else 0
    print(f"\n{'=' * 80}")
    print(f"SUMMARY: {model}")
    print(f"{'=' * 80}")
    print(f"\nOverall: {total_passed}/{total} ({total_passed/total*100:.0f}%)")
    print(f"Lemma correct: {total_lemma_ok}/{total} ({total_lemma_ok/total*100:.0f}%)")
    print(f"Related words correct: {total_rw_ok}/{total} ({total_rw_ok/total*100:.0f}%)")
    if total_rw_order_wrong > 0:
        print(f"  └─ Order wrong (content ok): {total_rw_order_wrong}")
    print(f"Avg response time: {avg_time:.0f}ms")

    print(f"\nBy Category:")
    for cat, stats in results_by_category.items():
        pct = stats["passed"] / stats["total"] * 100
        print(f"  {cat}: {stats['passed']}/{stats['total']} ({pct:.0f}%)")

    # Pass/Fail
    if total_passed / total >= 0.95:
        print(f"\n🎉 PASSED (≥95%)")
    elif total_passed / total >= 0.90:
        print(f"\n⚠️  CLOSE (90-95%)")
    else:
        print(f"\n❌ FAILED (<90%)")


def main():
    parser = argparse.ArgumentParser(description="Test reduced prompt accuracy")
    parser.add_argument(
        "--model",
        default="openai/gpt-4.1-mini",
        help="Model to test (default: openai/gpt-4.1-mini)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between requests in seconds (default: 0.5)"
    )
    parser.add_argument(
        "--test-prompt",
        action="store_true",
        help="Use test prompt (build_test_prompt) instead of main prompt"
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=100,
        help="Percentage of test cases to sample (default: 100, use 20 for 20%%)"
    )
    parser.add_argument(
        "--lang",
        choices=["de", "en"],
        default="de",
        help="Language to test: de (German) or en (English). Default: de"
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Start from this test case index (0-based). Useful for resuming interrupted runs."
    )
    parser.add_argument(
        "--end-index",
        type=int,
        default=None,
        help="End at this test case index (exclusive, 0-based). e.g., --start-index 70 --end-index 110"
    )
    args = parser.parse_args()

    # Select test cases based on language
    if args.lang == "en":
        test_cases = TEST_CASES_EN
        language = "English"
    else:
        test_cases = TEST_CASES_DE
        language = "German"

    asyncio.run(run_tests(args.model, args.delay, args.test_prompt, args.sample, test_cases, language, args.start_index, args.end_index))


if __name__ == "__main__":
    main()
