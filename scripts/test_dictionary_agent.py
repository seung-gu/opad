"""Test script for dictionary agent with tool use.

This script tests a new approach where:
1. LLM extracts lemma from context
2. LLM calls dictionary API tool
3. LLM selects appropriate definition based on context

Usage:
    PYTHONPATH=src uv run python src/scripts/test_dictionary_agent.py
    PYTHONPATH=src uv run python src/scripts/test_dictionary_agent.py --limit 10
    PYTHONPATH=src uv run python src/scripts/test_dictionary_agent.py --compare-models
"""

import os
import sys
# Suppress litellm proxy warnings
os.environ["LITELLM_LOG"] = "ERROR"

import argparse
import asyncio
import json
import time
from datetime import datetime

import httpx
import litellm
from dotenv import load_dotenv


class TeeLogger:
    """Write to both stdout and file."""
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def close(self):
        self.log.close()

# Load environment variables
load_dotenv()

# Dictionary API settings
FREE_DICTIONARY_API_BASE_URL = "https://freedictionaryapi.com/api/v1/entries"
API_TIMEOUT_SECONDS = 5.0

LANGUAGE_CODE_MAP = {
    "German": "de",
    "English": "en",
    "French": "fr",
    "Spanish": "es",
}

# Models to compare
MODELS = [
    "openai/gpt-4.1-mini",
    "openai/gpt-4.1",
    "gemini/gemini-2.0-flash",
    "gemini/gemini-2.5-flash",
    "anthropic/claude-3-haiku-20240307",
    "anthropic/claude-haiku-4-5-20251001",
    "anthropic/claude-sonnet-4-20250514",
]

MODEL_SHORT_NAMES = {
    "openai/gpt-4.1-mini": "gpt-4.1-mini",
    "openai/gpt-4.1": "gpt-4.1",
    "gemini/gemini-2.0-flash": "gemini-2.0",
    "gemini/gemini-2.5-flash": "gemini-2.5",
    "anthropic/claude-3-haiku-20240307": "haiku-3",
    "anthropic/claude-haiku-4-5-20251001": "haiku-4.5",
    "anthropic/claude-sonnet-4-20250514": "sonnet-4",
    "current": "current",
}

# Fallback pricing for models not in litellm's database (per 1M tokens)
FALLBACK_PRICING = {
    "anthropic/claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
}


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate cost using litellm, with fallback for missing models."""
    # Try litellm first
    try:
        prompt_cost, comp_cost = litellm.cost_per_token(
            model=model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        )
        return prompt_cost + comp_cost
    except Exception:
        pass

    # Fallback for models not in litellm
    pricing = FALLBACK_PRICING.get(model)
    if pricing:
        return (prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]) / 1_000_000

    return 0.0

# Tool definition for the LLM
DICTIONARY_TOOL = {
    "type": "function",
    "function": {
        "name": "lookup_dictionary",
        "description": "Look up a word in the dictionary API. Use the lemma (base form) of the word.",
        "parameters": {
            "type": "object",
            "properties": {
                "lemma": {
                    "type": "string",
                    "description": "The lemma (base/dictionary form) of the word to look up"
                },
                "language_code": {
                    "type": "string",
                    "enum": ["de", "en", "fr", "es"],
                    "description": "ISO 639-1 language code"
                }
            },
            "required": ["lemma", "language_code"]
        }
    }
}


SYSTEM_PROMPT = """You help language learners understand words in context.

Given a word and sentence:
1. Think like a language learner: what do they actually want to understand?
   - If the word is grammatically functional, find the content word it serves
   - If the word is part of an idiomatic expression, explain the full expression
   - Look up the word that carries the core meaning, not auxiliary elements
2. Look up the dictionary with the correct lemma
3. Select the definition matching THIS specific context

Return JSON with ALL applicable fields:
{
    "lemma": "dictionary form",
    "definition": "context-appropriate meaning",
    "pos": "noun/verb/adj/etc",
    "gender": "der/die/das (nouns)",
    "transitivity": "transitive/intransitive (verbs)",
    "reflexive": true/false (verbs),
    "auxiliary": "haben/sein (verbs)",
    "conjugations": {"present": "...", "past": "...", "participle": "..."},
    "level": "A1-C2 (CEFR level)",
}
"""


async def call_dictionary_api(lemma: str, language_code: str) -> dict | None:
    """Call the Free Dictionary API."""
    from urllib.parse import quote

    url = f"{FREE_DICTIONARY_API_BASE_URL}/{language_code}/{quote(lemma, safe='')}"

    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT_SECONDS) as client:
            response = await client.get(url)

            if response.status_code == 404:
                return {"error": f"Word '{lemma}' not found in dictionary"}

            response.raise_for_status()
            return response.json()

    except Exception as e:
        return {"error": str(e)}


async def run_agent(word: str, sentence: str, language: str, model: str = "openai/gpt-4.1-mini") -> tuple[dict, float, float]:
    """Run the dictionary agent and return result, time, and cost in USD."""

    language_code = LANGUAGE_CODE_MAP.get(language)
    if not language_code:
        return {"error": f"Language '{language}' not supported"}, 0, 0.0

    user_message = f"""Word: "{word}"
Sentence: "{sentence}"
Language: {language}

Please look up this word and provide the appropriate definition and grammatical information for this context."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]

    start_time = time.time()
    total_cost = 0.0

    # First LLM call - may include tool use
    response = await litellm.acompletion(
        model=model,
        messages=messages,
        tools=[DICTIONARY_TOOL],
        tool_choice="required",
        temperature=0,
        timeout=30
    )

    # Calculate cost using our pricing table
    cost = calculate_cost(model, response.usage.prompt_tokens, response.usage.completion_tokens)
    total_cost += cost

    assistant_message = response.choices[0].message

    # Check if tool was called
    tool_used = False

    if assistant_message.tool_calls:
        tool_used = True
        tool_call = assistant_message.tool_calls[0]
        function_args = json.loads(tool_call.function.arguments)

        print(f"     🔧 Tool: {function_args.get('lemma')} ({function_args.get('language_code')})")

        # Execute the tool
        api_result = await call_dictionary_api(
            lemma=function_args["lemma"],
            language_code=function_args["language_code"]
        )

        # Show API result summary
        if "error" in api_result:
            print(f"     └─ API ERROR: {api_result['error']}")
        else:
            entries = api_result.get("entries", [])
            if entries:
                senses_count = len(entries[0].get("senses", []))
                print(f"     └─ API OK: {senses_count} senses")

        # Add tool result to messages
        messages.append(assistant_message.model_dump())
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(api_result, ensure_ascii=False)[:8000]
        })

        # Second LLM call to process results
        # Include tools param for Anthropic compatibility
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            tools=[DICTIONARY_TOOL],
            temperature=0,
            timeout=30
        )

        # Add second call cost
        cost = calculate_cost(model, response.usage.prompt_tokens, response.usage.completion_tokens)
        total_cost += cost

        assistant_message = response.choices[0].message
    else:
        print(f"     ⚠️ NO TOOL CALLED")

    elapsed_time = time.time() - start_time

    # Parse the final response
    content = assistant_message.content or ""

    try:
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        if start_idx >= 0 and end_idx > start_idx:
            result = json.loads(content[start_idx:end_idx])
        else:
            result = {"raw_response": content, "error": "No JSON in response"}
    except json.JSONDecodeError:
        result = {"raw_response": content, "error": "Invalid JSON"}

    return result, elapsed_time, total_cost


async def run_current_approach(word: str, sentence: str, language: str) -> tuple[dict, float, float]:
    """Run the current hybrid approach for comparison."""
    from services.dictionary_service import DictionaryService, LookupRequest

    service = DictionaryService()
    request = LookupRequest(word=word, sentence=sentence, language=language)

    start_time = time.time()
    result = await service.lookup(request)
    elapsed_time = time.time() - start_time

    stats = service.last_token_stats
    total_cost = 0.0
    if stats:
        # Current approach uses gpt-4.1-mini
        total_cost = calculate_cost(stats.model or "gpt-4.1-mini", stats.prompt_tokens, stats.completion_tokens)

    return {
        "lemma": result.lemma,
        "definition": result.definition,
        "pos": result.pos,
        "gender": result.gender,
        "phonetics": result.phonetics,
        "conjugations": result.conjugations,
        "level": result.level,
        "source": result.source
    }, elapsed_time, total_cost


def fetch_vocabularies(language: str | None, limit: int, randomize: bool = True):
    """Fetch vocabularies from MongoDB."""
    import random
    from utils.mongodb import get_vocabulary_counts

    # Fetch more than needed if randomizing
    fetch_limit = limit * 10 if randomize else limit

    vocabs = get_vocabulary_counts(
        language=language,
        user_id=None,
        skip=0,
        limit=fetch_limit
    )

    # Filter to only supported languages
    supported = [v for v in vocabs if v.get("language") in LANGUAGE_CODE_MAP]

    if randomize and len(supported) > limit:
        return random.sample(supported, limit)

    return supported[:limit]


async def run_model_comparison(vocabs: list, models: list):
    """Compare multiple models on the same vocabulary set."""

    print("\n" + "=" * 80)
    print("🔬 MODEL COMPARISON MODE")
    print("=" * 80)
    print(f"Models: {', '.join(MODEL_SHORT_NAMES.get(m, m) for m in models)}")
    print(f"Test cases: {len(vocabs)}")
    print("=" * 80)

    # Stats per model (costs in USD)
    model_stats = {m: {"times": [], "costs": [], "scores": []} for m in models}
    model_stats["current"] = {"times": [], "costs": [], "scores": []}

    for i, vocab in enumerate(vocabs, 1):
        word = vocab.get("word", "")
        sentence = vocab.get("sentence", "")
        language = vocab.get("language", "English")

        if language not in LANGUAGE_CODE_MAP:
            continue

        print(f"\n{'='*80}")
        print(f"[{i}/{len(vocabs)}] {word}")
        print(f"Sentence: {sentence[:70]}...")
        print("-" * 80)

        all_results = {}

        # Run current approach first
        print(f"\n📚 current:")
        try:
            result, elapsed, cost = await run_current_approach(word, sentence, language)
            model_stats["current"]["times"].append(elapsed)
            model_stats["current"]["costs"].append(cost)
            all_results["current"] = result
            print(f"   ⏱️ {elapsed:.1f}s | 💰 ${cost:.6f}/call")
            print(f"   Def: {str(result.get('definition', 'N/A'))[:60]}")
            print(f"   POS: {result.get('pos', '-')} | Level: {result.get('level', '-')}")
            if result.get("pos") in ["verb", "Verb"]:
                conj = result.get("conjugations", {})
                print(f"   Trans/Refl/Aux: -/-/{conj.get('auxiliary', '-') if conj else '-'}")
                if conj:
                    print(f"   Conj: {conj}")
            if result.get("pos") in ["noun", "Noun", "Nomen"]:
                print(f"   Gender: {result.get('gender', '-')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            all_results["current"] = {"error": str(e)}

        # Run each model
        for model in models:
            short_name = MODEL_SHORT_NAMES.get(model, model)
            print(f"\n🤖 {short_name}:")
            try:
                result, elapsed, cost = await run_agent(word, sentence, language, model)
                model_stats[model]["times"].append(elapsed)
                model_stats[model]["costs"].append(cost)
                all_results[model] = result

                print(f"   ⏱️ {elapsed:.1f}s | 💰 ${cost:.6f}/call")
                print(f"   Def: {str(result.get('definition', 'N/A'))[:60]}")
                print(f"   POS: {result.get('pos', '-')} | Level: {result.get('level', '-')}")
                if result.get("pos") in ["verb", "Verb"]:
                    print(f"   Trans/Refl/Aux: {result.get('transitivity', '-')}/{result.get('reflexive', '-')}/{result.get('auxiliary', '-')}")
                    conj = result.get("conjugations", {})
                    if conj:
                        print(f"   Conj: {conj}")
                if result.get("pos") in ["noun", "Noun", "Nomen"]:
                    print(f"   Gender: {result.get('gender', '-')}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
                all_results[model] = {"error": str(e)}

            await asyncio.sleep(0.3)

        # Quick evaluation - score each result (accuracy + speed + cost)
        print(f"\n🧑‍⚖️ EVAL:")
        try:
            # Collect times and costs for models that ran successfully this round
            round_times = {}
            round_costs = {}
            for k in ["current"] + models:
                if k in all_results and "error" not in all_results[k]:
                    if k == "current" and model_stats["current"]["times"]:
                        round_times[k] = model_stats["current"]["times"][-1]
                        round_costs[k] = model_stats["current"]["costs"][-1] if model_stats["current"]["costs"] else 0
                    elif k in model_stats and model_stats[k]["times"]:
                        round_times[k] = model_stats[k]["times"][-1]
                        round_costs[k] = model_stats[k]["costs"][-1] if model_stats[k]["costs"] else 0

            # Speed scoring: ≤1.5s = 10점, ≥4.5s = 4점, linear, min 0
            # Formula: score = max(0, min(10, 13 - 2*t))
            speed_scores = {}
            for k, t in round_times.items():
                name = MODEL_SHORT_NAMES.get(k, k)
                score = max(0, min(10, 13 - 2 * t))
                speed_scores[name] = round(score, 1)

            # Cost scoring: actual USD cost per call
            # $0.0002 = 10점, $0.02 = 3점, linear
            cost_scores = {}
            for k, cost in round_costs.items():
                name = MODEL_SHORT_NAMES.get(k, k)
                score = max(0, min(10, 10.07 - cost * 353.54))
                cost_scores[name] = round(score, 1)

            eval_prompt = f"""Word: "{word}" in "{sentence}" ({language})

FOR LANGUAGE LEARNERS: The goal is to help learners understand the MEANINGFUL word, not just the literal highlighted word.
- If "hat" is highlighted in "sich verbreitet hat", the learner wants to know about "verbreiten", not the auxiliary "haben"
- If "sich" is highlighted, find the verb it belongs to
- Always identify the SEMANTICALLY MEANINGFUL unit

STEP 1: Determine the CORRECT answer for language learning:
- What word should a learner look up to understand this sentence?
- What is the useful definition?

STEP 2: Rate each result 1-10 based on your answer.
STRICT SCORING - deduct points for missing/wrong information:

REQUIRED for all words:
- Lemma:
  * Wrong semantic unit (looked up wrong word entirely): score = 0
  * Correct word but wrong form: -1
- Definition correct for context: -1 if wrong/missing
- Part of speech (pos): -1 if wrong/missing

REQUIRED for VERBS:
- transitivity (transitive/intransitive): -1 if wrong/missing
- reflexive (true/false for sich-verbs): -1 if wrong/missing
- auxiliary (haben/sein): -1 if wrong/missing
- conjugations (present/past/participle): -1 if wrong/missing

REQUIRED for NOUNS:
- gender (der/die/das): -2 if wrong/missing

Start at 10, subtract for each missing/wrong item.

"""
            for key, res in all_results.items():
                name = MODEL_SHORT_NAMES.get(key, key)
                eval_prompt += f"{name}: {json.dumps(res, ensure_ascii=False)[:400]}\n"

            eval_prompt += '\nReturn JSON: {"correct_lemma": "your answer", "accuracy_scores": {"model_name": score}, "best_accuracy": "model_name", "reason": "Korean explanation"}'

            eval_response = await litellm.acompletion(
                model="anthropic/claude-sonnet-4-20250514",
                messages=[{"role": "user", "content": eval_prompt}],
                temperature=0,
                timeout=30
            )

            eval_content = eval_response.choices[0].message.content
            si = eval_content.find('{')
            ei = eval_content.rfind('}') + 1
            if si >= 0:
                eval_result = json.loads(eval_content[si:ei])
                correct_lemma = eval_result.get("correct_lemma", "")
                accuracy_scores = eval_result.get("accuracy_scores", {})
                best_accuracy = eval_result.get("best_accuracy", "")
                reason = eval_result.get("reason", "")
                print(f"   ✅ Correct: {correct_lemma}")

                # Calculate combined scores (accuracy * 0.5 + speed * 0.3 + cost * 0.2)
                print(f"   {'Model':<12} {'Acc':<5} {'Spd':<5} {'Cst':<5} {'Time':<6} {'$/call':<10} {'Comb':<6}")
                print(f"   {'-'*58}")

                combined_scores = {}
                for key in ["current"] + models:
                    name = MODEL_SHORT_NAMES.get(key, key)
                    acc = accuracy_scores.get(name, accuracy_scores.get(key, 0))
                    if not isinstance(acc, (int, float)):
                        acc = 0
                    spd = speed_scores.get(name, 0)
                    cst = cost_scores.get(name, 0)
                    actual_time = round_times.get(key, 0)
                    actual_cost = round_costs.get(key, 0)

                    combined = round(acc * 0.5 + spd * 0.3 + cst * 0.2, 1)
                    combined_scores[name] = combined
                    if acc > 0:
                        model_stats[key]["scores"].append(combined)
                    print(f"   {name:<12} {acc:<5} {spd:<5.1f} {cst:<5.1f} {actual_time:<6.1f}s ${actual_cost:<9.5f} {combined:<6}")

                if combined_scores:
                    best_combined = max(combined_scores, key=combined_scores.get)
                    print(f"   🎯 Accuracy: {best_accuracy} | 🏆 Overall: {best_combined}")
                print(f"   💬 {reason[:60]}")

        except Exception as e:
            print(f"   ❌ Eval error: {e}")

    # Final summary
    print("\n" + "=" * 80)
    print("📊 FINAL SUMMARY (Combined Score = Accuracy×0.5 + Speed×0.3 + Cost×0.2)")
    print("=" * 80)

    print(f"\n{'Model':<15} {'Avg Time':<10} {'Avg Cost/call':<14} {'Combined':<10}")
    print("-" * 52)

    summary_data = []
    for key in ["current"] + models:
        name = MODEL_SHORT_NAMES.get(key, key)
        stats = model_stats[key]

        avg_time = sum(stats["times"]) / len(stats["times"]) if stats["times"] else 0
        avg_cost = sum(stats["costs"]) / len(stats["costs"]) if stats["costs"] else 0
        avg_score = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0

        print(f"{name:<15} {avg_time:<10.2f}s ${avg_cost:<13.6f} {avg_score:<10.1f}/10")
        summary_data.append((name, avg_time, avg_cost, avg_score))

    # Best model
    if summary_data:
        best_overall = max(summary_data, key=lambda x: x[3])
        best_by_speed = min([s for s in summary_data if s[1] > 0], key=lambda x: x[1])
        best_by_cost = min([s for s in summary_data if s[2] > 0], key=lambda x: x[2])

        print(f"\n🏆 Best Overall: {best_overall[0]} ({best_overall[3]:.1f}/10)")
        print(f"⚡ Fastest: {best_by_speed[0]} ({best_by_speed[1]:.2f}s)")
        print(f"💰 Cheapest: {best_by_cost[0]} (${best_by_cost[2]:.6f}/call)")


async def run_single_model(vocabs: list, model: str):
    """Test single model vs current approach."""

    print("=" * 70)
    print(f"Dictionary Agent Test - {MODEL_SHORT_NAMES.get(model, model)} vs Current")
    print("=" * 70)

    agent_times, agent_costs_list = [], []
    current_times, current_costs_list = [], []
    wins = {"agent": 0, "current": 0, "tie": 0}

    for i, vocab in enumerate(vocabs, 1):
        word = vocab.get("word", "")
        sentence = vocab.get("sentence", "")
        language = vocab.get("language", "English")

        if language not in LANGUAGE_CODE_MAP:
            continue

        print(f"\n{'='*70}")
        print(f"[{i}/{len(vocabs)}] {word}")
        print(f"Sentence: {sentence[:70]}...")
        print("-" * 70)

        # Run agent
        print(f"\n🤖 AGENT ({MODEL_SHORT_NAMES.get(model, model)}):")
        agent_result = {}
        try:
            agent_result, agent_time, agent_cost = await run_agent(word, sentence, language, model)
            agent_times.append(agent_time)
            agent_costs_list.append(agent_cost)

            print(f"   ⏱️ {agent_time:.1f}s | 💰 ${agent_cost*1000:.4f}/1k")
            print(f"   Definition: {str(agent_result.get('definition', 'N/A'))[:70]}")
            if agent_result.get("pos") in ["verb", "Verb"]:
                print(f"   Trans: {agent_result.get('transitivity', 'N/A')} | Refl: {agent_result.get('reflexive', 'N/A')} | Aux: {agent_result.get('auxiliary', 'N/A')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Run current
        print(f"\n📚 CURRENT:")
        current_result = {}
        try:
            current_result, current_time, current_cost = await run_current_approach(word, sentence, language)
            current_times.append(current_time)
            current_costs_list.append(current_cost)

            print(f"   ⏱️ {current_time:.1f}s | 💰 ${current_cost*1000:.4f}/1k")
            print(f"   Definition: {str(current_result.get('definition', 'N/A'))[:70]}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Evaluate
        if agent_result and current_result and "error" not in agent_result:
            print(f"\n🧑‍⚖️ EVAL:")
            try:
                eval_prompt = f"""Word "{word}" in "{sentence}" ({language})

AGENT: {json.dumps(agent_result, ensure_ascii=False)[:500]}
CURRENT: {json.dumps(current_result, ensure_ascii=False)[:500]}

Which is better for language learning? Return JSON:
{{"agent_score": 1-10, "current_score": 1-10, "winner": "agent/current/tie", "reason": "Korean"}}"""

                resp = await litellm.acompletion(
                    model="anthropic/claude-sonnet-4-20250514",
                    messages=[{"role": "user", "content": eval_prompt}],
                    temperature=0,
                    timeout=30
                )
                content = resp.choices[0].message.content
                si, ei = content.find('{'), content.rfind('}') + 1
                if si >= 0:
                    ev = json.loads(content[si:ei])
                    print(f"   Agent: {ev.get('agent_score', '?')}/10 | Current: {ev.get('current_score', '?')}/10")
                    print(f"   🏆 {ev.get('winner', '').upper()} - {ev.get('reason', '')[:60]}")
                    winner = ev.get("winner", "tie")
                    if winner in wins:
                        wins[winner] += 1
            except Exception as e:
                print(f"   ❌ {e}")

        await asyncio.sleep(0.5)

    # Summary
    if agent_times and current_times:
        print("\n" + "=" * 70)
        print("📊 SUMMARY")
        print("=" * 70)

        avg_agent_time = sum(agent_times) / len(agent_times)
        avg_current_time = sum(current_times) / len(current_times)
        avg_agent_cost = sum(agent_costs_list) / len(agent_costs_list)
        avg_current_cost = sum(current_costs_list) / len(current_costs_list)

        print(f"\n{'Metric':<15} {'Agent':<18} {'Current':<18}")
        print("-" * 55)
        print(f"{'Avg Time':<15} {avg_agent_time:.2f}s{'':<13} {avg_current_time:.2f}s")
        print(f"{'Avg Cost/call':<15} ${avg_agent_cost:.6f}{'':<6} ${avg_current_cost:.6f}")

        total_evals = wins["agent"] + wins["current"] + wins["tie"]
        if total_evals > 0:
            print(f"\n🏆 WINS: Agent {wins['agent']}/{total_evals} | Current {wins['current']}/{total_evals} | Tie {wins['tie']}/{total_evals}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test dictionary agent with DB data")
    parser.add_argument("--limit", type=int, default=5, help="Number of words to test")
    parser.add_argument("--language", type=str, default=None, help="Filter by language")
    parser.add_argument("--model", type=str, default="openai/gpt-4.1-mini", help="Model for single test")
    parser.add_argument("--no-random", action="store_true", help="Don't randomize")
    parser.add_argument("--compare-models", action="store_true", help="Compare all models")
    parser.add_argument("--no-log", action="store_true", help="Don't save log file")
    args = parser.parse_args()

    # Set up logging to file
    logger = None
    if not args.no_log:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"dictionary_agent_{timestamp}.log"
        logger = TeeLogger(log_filename)
        sys.stdout = logger
        print(f"📝 Logging to: {log_filename}\n")

    try:
        # Fetch from DB
        vocabs = fetch_vocabularies(args.language, args.limit, randomize=not args.no_random)

        if not vocabs:
            print("No vocabularies found in database!")
            return

        print(f"Found {len(vocabs)} vocabularies")

        if args.compare_models:
            await run_model_comparison(vocabs, MODELS)
        else:
            await run_single_model(vocabs, args.model)
    finally:
        if logger:
            sys.stdout = logger.terminal
            logger.close()
            print(f"\n📝 Log saved to: {log_filename}")


if __name__ == "__main__":
    asyncio.run(main())
