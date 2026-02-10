"""Benchmark: LLM entry+sense selection accuracy.

Tests whether an LLM can correctly select the right dictionary entry and sense
when the Free Dictionary API returns multiple entries/senses for a word.

For each test case:
  1. Call Free Dictionary API with the expected lemma
  2. If multiple entries or senses exist, ask LLM to select the best one
  3. Grade the selection with a separate LLM (grading agent)
  4. Report accuracy

Usage:
    PYTHONPATH=src uv run python scripts/benchmark_entry_selection.py
    PYTHONPATH=src uv run python scripts/benchmark_entry_selection.py --language German --limit 10
    PYTHONPATH=src uv run python scripts/benchmark_entry_selection.py --shuffle --seed 123
"""

import argparse
import asyncio
import logging
import random
import re
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

import httpx
from litellm import acompletion, cost_per_token

# Import test cases
sys.path.insert(0, "scripts")
from test_cases import TEST_CASES_DE, TEST_CASES_EN

from utils.dictionary_api import (
    FREE_DICTIONARY_API_BASE_URL,
    API_TIMEOUT_SECONDS,
    LANGUAGE_CODE_MAP,
)
from utils.dictionary_api import _strip_reflexive_pronoun

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────

@dataclass
class BenchmarkResult:
    """Result for a single test case."""
    sentence: str
    word: str
    lemma: str
    category: str
    # API data
    api_entries: list[dict[str, Any]] = field(default_factory=list)
    api_entry_count: int = 0
    total_sense_count: int = 0
    # LLM selection
    selected_entry: int = 0
    selected_sense: int = 0
    selected_subsense: int = -1  # -1 = sense level, 0+ = subsense index
    selected_pos: str = ""
    selected_definition: str = ""
    # Grading
    grade: str = ""           # "correct" / "incorrect" / "unknown"
    grade_reason: str = ""
    # Timing & usage (LLM selection only, excludes grading agent)
    llm_latency: float = 0.0
    llm_prompt_tokens: int = 0
    llm_completion_tokens: int = 0
    # Status
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class BenchmarkStats:
    """Aggregate statistics."""
    total: int = 0
    api_found: int = 0
    api_not_found: int = 0
    single: int = 0           # 1 entry, 1 sense (no selection needed)
    needs_selection: int = 0  # multi-entry or multi-sense
    correct: int = 0
    incorrect: int = 0
    unknown: int = 0
    by_category: dict[str, dict[str, int]] = field(default_factory=dict)


def normalize_pos(pos: str | None) -> str:
    """Normalize API POS string."""
    if not pos:
        return "unknown"
    p = pos.lower()
    if "adverb" in p: return "adverb"
    if "verb" in p: return "verb"
    if "noun" in p: return "noun"
    if "adjective" in p or "adjektiv" in p: return "adjective"
    if "preposition" in p: return "preposition"
    if "conjunction" in p: return "conjunction"
    if "article" in p: return "article"
    return p


# ─────────────────────────────────────────────────
# API cache
# ─────────────────────────────────────────────────

_api_cache: dict[str, dict[str, Any] | None] = {}


async def fetch_api_entries(lemma: str, language: str) -> dict[str, Any] | None:
    """Fetch all entries from Free Dictionary API (cached)."""
    language_code = LANGUAGE_CODE_MAP.get(language)
    if not language_code:
        return None

    lookup_word = _strip_reflexive_pronoun(lemma, language_code)
    cache_key = f"{language_code}:{lookup_word}"

    if cache_key in _api_cache:
        return _api_cache[cache_key]

    url = f"{FREE_DICTIONARY_API_BASE_URL}/{language_code}/{quote(lookup_word, safe='')}"
    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT_SECONDS) as client:
            response = await client.get(url)
            if response.status_code == 404:
                _api_cache[cache_key] = None
                return None
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                _api_cache[cache_key] = None
                return None
            _api_cache[cache_key] = data
            return data
    except Exception as e:
        logger.warning(f"API error for {lookup_word}: {e}")
        _api_cache[cache_key] = None
        return None


# ─────────────────────────────────────────────────
# LLM: select entry+sense
# ─────────────────────────────────────────────────

async def select_entry_sense(
    sentence: str,
    word: str,
    entries: list[dict[str, Any]],
    model: str,
) -> tuple[int, int, int, float, int, int]:
    """LLM selects the best entry+sense+subsense.

    Returns (entry_idx, sense_idx, subsense_idx, latency, prompt_tokens, completion_tokens).
    subsense_idx = -1 means sense-level selection (no subsense).
    """
    options = []
    for i, entry in enumerate(entries):
        pos = entry.get("partOfSpeech", "unknown")
        senses = entry.get("senses", [])
        options.append(f"entries[{i}] ({pos}):")
        for j, sense in enumerate(senses):
            defn = sense.get("definition", "")
            options.append(f"  {i}.{j} {defn}")
            for k, sub in enumerate(sense.get("subsenses", [])):
                subdef = sub.get("definition", "")
                options.append(f"    {i}.{j}.{k} {subdef}")

    prompt = f"""Sentence: "{sentence}"
Word: "{word}"

Which definition best matches the word usage in this sentence?
Reply with the number only (e.g. 1.0 or 0.0.1 for a subsense).

{chr(10).join(options)}"""

    t0 = time.time()
    try:
        response = await acompletion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=10,
            timeout=15,
        )
        latency = time.time() - t0
        content = response.choices[0].message.content.strip()
        usage = getattr(response, "usage", None)
        pt = getattr(usage, "prompt_tokens", 0) if usage else 0
        ct = getattr(usage, "completion_tokens", 0) if usage else 0

        # Parse "X.Y" or "X.Y.Z" → entries[X].senses[Y].subsenses[Z]
        match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", content)
        if match:
            ei, si = int(match.group(1)), int(match.group(2))
            if 0 <= ei < len(entries):
                senses = entries[ei].get("senses", [])
                si = max(0, min(si, len(senses) - 1)) if senses else 0
                ssi = -1
                if match.group(3) and senses:
                    raw_ssi = int(match.group(3))
                    subsenses = senses[si].get("subsenses", [])
                    ssi = max(0, min(raw_ssi, len(subsenses) - 1)) if subsenses else -1
                return ei, si, ssi, latency, pt, ct

        # Fallback: single number → entry index, sense 0
        match = re.search(r"\d+", content)
        if match:
            ei = int(match.group())
            if 0 <= ei < len(entries):
                return ei, 0, -1, latency, pt, ct

    except Exception as e:
        logger.warning(f"LLM selection failed: {e}")
        latency = time.time() - t0

    return 0, 0, -1, latency, 0, 0


# ─────────────────────────────────────────────────
# Grading agent
# ─────────────────────────────────────────────────

async def grade_selection(
    sentence: str,
    lemma: str,
    pos: str,
    definition: str,
) -> tuple[str, str]:
    """Grade whether a selected definition is correct for the context.

    Uses a separate model (Claude Sonnet) for independent grading.
    Returns (grade, reason).
    """
    prompt = f"""Sentence: "{sentence}"
Lemma: "{lemma}"
Selected POS: {pos}
Selected definition: "{definition}"

Is this the correct part of speech and definition for how "{lemma}" is used in this sentence?
Reply in this exact format:
GRADE: correct OR incorrect
REASON: one sentence explanation"""

    try:
        response = await acompletion(
            model="anthropic/claude-sonnet-4-20250514",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=60,
            timeout=15,
        )
        content = response.choices[0].message.content.strip()
        first_line = content.split("\n")[0].lower()
        grade = "correct" if "correct" in first_line and "incorrect" not in first_line else "incorrect"
        reason_match = re.search(r"REASON:\s*(.+)", content, re.IGNORECASE)
        reason = reason_match.group(1).strip() if reason_match else content
        return grade, reason
    except Exception as e:
        logger.warning(f"Grading failed: {e}")
        return "unknown", str(e)


# ─────────────────────────────────────────────────
# Benchmark runner
# ─────────────────────────────────────────────────

async def benchmark_single(
    test_case: tuple,
    language: str,
    model: str,
) -> BenchmarkResult:
    """Run benchmark for a single test case."""
    sentence, word, expected_lemma, _related, category = test_case
    result = BenchmarkResult(sentence=sentence, word=word, lemma=expected_lemma, category=category)

    # Fetch API
    data = await fetch_api_entries(expected_lemma, language)
    if data is None:
        result.skipped = True
        result.skip_reason = "API not found"
        return result

    entries = data.get("entries", [])
    if not entries:
        result.skipped = True
        result.skip_reason = "No entries"
        return result

    result.api_entries = entries
    result.api_entry_count = len(entries)
    total_senses = sum(len(e.get("senses", [])) for e in entries)
    total_subsenses = sum(
        len(s.get("subsenses", []))
        for e in entries for s in e.get("senses", [])
    )
    result.total_sense_count = total_senses + total_subsenses

    needs_selection = len(entries) > 1 or total_senses > 1 or total_subsenses > 0

    if needs_selection:
        # LLM selects
        ei, si, ssi, latency, pt, ct = await select_entry_sense(sentence, word, entries, model)
        result.selected_entry = ei
        result.selected_sense = si
        result.selected_subsense = ssi
        result.llm_latency = latency
        result.llm_prompt_tokens = pt
        result.llm_completion_tokens = ct
    else:
        result.selected_entry = 0
        result.selected_sense = 0

    # Get selected info
    entry = entries[result.selected_entry]
    result.selected_pos = normalize_pos(entry.get("partOfSpeech"))
    senses = entry.get("senses", [])
    if result.selected_sense < len(senses):
        sense = senses[result.selected_sense]
        if result.selected_subsense >= 0:
            subsenses = sense.get("subsenses", [])
            if result.selected_subsense < len(subsenses):
                result.selected_definition = subsenses[result.selected_subsense].get("definition", "")
            else:
                result.selected_definition = sense.get("definition", "")
        else:
            result.selected_definition = sense.get("definition", "")

    # Grade (only for multi cases)
    if needs_selection:
        result.grade, result.grade_reason = await grade_selection(
            sentence, expected_lemma, result.selected_pos, result.selected_definition
        )
    else:
        result.grade = "skipped"

    return result


def _print_case_detail(r: BenchmarkResult, index: int, total: int, model: str = "") -> None:
    """Print detailed per-case output during benchmark run."""
    mark = {"correct": "✅", "incorrect": "❌", "skipped": "⏭️"}.get(r.grade, "❓")

    # Build cost/token info line
    stats_parts = []
    if r.llm_latency > 0:
        stats_parts.append(f"{r.llm_latency:.2f}s")
    tok = r.llm_prompt_tokens + r.llm_completion_tokens
    if tok > 0:
        stats_parts.append(f"{tok} tok")
        if model:
            try:
                pc, cc = cost_per_token(model=model, prompt_tokens=r.llm_prompt_tokens, completion_tokens=r.llm_completion_tokens)
                stats_parts.append(f"${pc + cc:.6f}")
            except Exception:
                pass
    stats_str = f"  ⚡ {' | '.join(stats_parts)}" if stats_parts else ""

    print(f"\n{mark} [{index}/{total}] {r.lemma}  word=\"{r.word}\"  ({r.category}){stats_str}")
    print(f"  📝 \"{r.sentence}\"")

    if r.skipped:
        print(f"  ⏭️  SKIPPED: {r.skip_reason}")
        return

    # All entries + senses + subsenses
    for i, entry in enumerate(r.api_entries):
        pos = entry.get("partOfSpeech", "?")
        marker = " 👈" if i == r.selected_entry else ""
        print(f"  entries[{i}] ({pos}){marker}")
        for j, sense in enumerate(entry.get("senses", [])):
            defn = sense.get("definition", "")[:120]
            is_sense_sel = i == r.selected_entry and j == r.selected_sense and r.selected_subsense < 0
            sel = " ⭐" if is_sense_sel else ""
            print(f"    [{i}.{j}] {defn}{sel}")
            for k, sub in enumerate(sense.get("subsenses", [])):
                subdef = sub.get("definition", "")[:120]
                is_sub_sel = i == r.selected_entry and j == r.selected_sense and k == r.selected_subsense
                ssel = " ⭐" if is_sub_sel else ""
                print(f"      [{i}.{j}.{k}] {subdef}{ssel}")

    # LLM selection
    sel_label = f"{r.selected_entry}.{r.selected_sense}"
    if r.selected_subsense >= 0:
        sel_label += f".{r.selected_subsense}"
    print(f"  🤖 LLM: [{sel_label}] ({r.selected_pos}) {r.selected_definition[:100]}")

    # Grading
    if r.grade != "skipped":
        grade_icon = "✅" if r.grade == "correct" else "❌"
        print(f"  {grade_icon} Grade: {r.grade}  — {r.grade_reason}")


async def run_benchmark(
    language: str,
    model: str,
    limit: int | None = None,
    shuffle: bool = False,
    seed: int | None = None,
) -> list[BenchmarkResult]:
    """Run benchmark on all test cases for a language."""
    test_cases = list(TEST_CASES_DE if language == "German" else TEST_CASES_EN)
    if shuffle:
        rng = random.Random(seed)
        rng.shuffle(test_cases)
        print(f"  Shuffled (seed={seed})")
    if limit:
        limit = max(1, min(limit, 100))
        count = max(1, len(test_cases) * limit // 100)
        test_cases = test_cases[:count]

    results: list[BenchmarkResult] = []
    total = len(test_cases)

    for i, tc in enumerate(test_cases):
        result = await benchmark_single(tc, language, model)
        results.append(result)
        _print_case_detail(result, i + 1, total, model)
        await asyncio.sleep(0.1)

    return results


# ─────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────

def print_report(results: list[BenchmarkResult], language: str, model: str = "") -> None:
    """Print benchmark report."""
    stats = BenchmarkStats()
    stats.total = len(results)

    for r in results:
        if r.skipped:
            stats.api_not_found += 1
            continue

        stats.api_found += 1

        if r.grade == "skipped":
            stats.single += 1
            continue

        stats.needs_selection += 1
        if r.grade == "correct":
            stats.correct += 1
        elif r.grade == "incorrect":
            stats.incorrect += 1
        else:
            stats.unknown += 1

        # Per-category
        cat = r.category
        if cat not in stats.by_category:
            stats.by_category[cat] = {"total": 0, "correct": 0, "incorrect": 0}
        stats.by_category[cat]["total"] += 1
        if r.grade == "correct":
            stats.by_category[cat]["correct"] += 1
        elif r.grade == "incorrect":
            stats.by_category[cat]["incorrect"] += 1

    # ── Summary ──
    print(f"\n{'='*70}")
    print(f"  Entry+Sense Selection Benchmark — {language}")
    print(f"{'='*70}")

    print(f"\n  Total test cases:        {stats.total}")
    print(f"  API found:               {stats.api_found}")
    print(f"  API not found:           {stats.api_not_found}")
    print(f"  Single (no selection):    {stats.single}")
    print(f"  Multi (LLM selected):    {stats.needs_selection}")

    if stats.needs_selection > 0:
        pct = stats.correct / stats.needs_selection * 100
        print(f"\n  Selection Accuracy ({stats.needs_selection} cases):")
        print(f"    Correct:    {stats.correct:>4}  ({pct:.1f}%)")
        print(f"    Incorrect:  {stats.incorrect:>4}  ({100 - pct:.1f}%)")
        if stats.unknown:
            print(f"    Unknown:    {stats.unknown:>4}")

    # LLM latency stats
    latencies = [r.llm_latency for r in results if r.llm_latency > 0]
    if latencies:
        avg_lat = sum(latencies) / len(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)
        print(f"\n  LLM Latency ({len(latencies)} calls):")
        print(f"    Avg:  {avg_lat:.2f}s")
        print(f"    Min:  {min_lat:.2f}s")
        print(f"    Max:  {max_lat:.2f}s")

    # LLM token & cost stats
    total_pt = sum(r.llm_prompt_tokens for r in results)
    total_ct = sum(r.llm_completion_tokens for r in results)
    total_tokens = total_pt + total_ct
    if total_tokens > 0:
        print(f"\n  LLM Tokens (selection only, excludes grading):")
        print(f"    Prompt:      {total_pt:>8}")
        print(f"    Completion:  {total_ct:>8}")
        print(f"    Total:       {total_tokens:>8}")
        if model:
            try:
                prompt_cost, completion_cost = cost_per_token(model=model, prompt_tokens=total_pt, completion_tokens=total_ct)
                total_cost = prompt_cost + completion_cost
                print(f"    Cost:        ${total_cost:.6f}")
            except Exception:
                pass

    # Per-category
    if stats.by_category:
        col_w = 20
        print(f"\n  {'Category':<{col_w}} {'Total':>6} {'Correct':>8} {'Incorrect':>10} {'Accuracy':>10}")
        print(f"  {'-'*54}")
        for cat, s in sorted(stats.by_category.items(), key=lambda x: -x[1]["total"]):
            pct = s["correct"] / s["total"] * 100 if s["total"] > 0 else 0
            # wide chars (한글, CJK) take 2 columns in terminal
            display_w = sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in cat)
            pad = col_w - display_w
            print(f"  {cat}{' ' * max(pad, 1)} {s['total']:>6} {s['correct']:>8} {s['incorrect']:>10} {pct:>9.1f}%")

    print(f"\n{'='*70}")


class TeeWriter:
    """Write to both stdout and a file."""

    def __init__(self, file):
        self.terminal = sys.stdout
        self.file = file

    def write(self, text):
        self.terminal.write(text)
        self.file.write(text)

    def flush(self):
        self.terminal.flush()
        self.file.flush()


def main():
    parser = argparse.ArgumentParser(description="Benchmark entry+sense selection accuracy")
    parser.add_argument("--language", choices=["German", "English", "both"], default="both")
    parser.add_argument("--model", default="openai/gpt-4.1-mini", help="Model for selection")
    parser.add_argument("--limit", type=int, default=None, help="Percentage of test cases to run (1-100)")
    parser.add_argument("--shuffle", action="store_true", help="Shuffle test cases")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for shuffle")
    parser.add_argument("--output", type=str, default=None, help="Save output to txt file")
    args = parser.parse_args()

    output_file = None
    original_stdout = sys.stdout
    if args.output:
        output_file = open(args.output, "w", encoding="utf-8")
        sys.stdout = TeeWriter(output_file)

    try:
        languages = ["German", "English"] if args.language == "both" else [args.language]

        start = time.time()
        for lang in languages:
            print(f"\nRunning {lang} benchmark...")
            results = asyncio.run(run_benchmark(lang, args.model, args.limit, args.shuffle, args.seed))
            print_report(results, lang, args.model)

        elapsed = time.time() - start
        print(f"\nTotal time: {elapsed:.1f}s")

        if args.output:
            print(f"\nOutput saved to: {args.output}", file=original_stdout)
    finally:
        if output_file:
            sys.stdout = original_stdout
            output_file.close()


if __name__ == "__main__":
    main()
