"""Lemma extraction module — Step 1 of the dictionary lookup pipeline.

Extracts lemma + related_words + CEFR level from a word in context.
German uses NLP adapter (Stanza, ~51ms); other languages use LLM (~800ms).
Both paths return the same dict format: {"lemma", "related_words", "level"}.
"""

import logging
from typing import Any, TypedDict

from json_repair import repair_json
from port.llm import LLMPort
from port.nlp import NLPPort
from domain.model.token_usage import LLMCallResult

logger = logging.getLogger(__name__)


class LemmaResult(TypedDict):
    """Typed result of lemma extraction (Step 1 of lookup pipeline)."""
    lemma: str
    related_words: list[str] | None
    level: str | None

# Token limits
_REDUCED_PROMPT_MAX_TOKENS = 200
_CEFR_PROMPT_MAX_TOKENS = 10


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

async def extract_lemma(
    word: str,
    sentence: str,
    language: str,
    llm: LLMPort,
    nlp: NLPPort | None = None,
    model: str = "openai/gpt-4.1-mini",
) -> tuple[LemmaResult | None, LLMCallResult | None]:
    """Extract lemma, related_words, and CEFR level for a word in context.

    German uses NLP adapter with a small LLM call for CEFR.
    Other languages use LLM reduced prompt.

    Returns:
        Tuple of (LemmaResult, token_stats).
        Returns (None, None) on failure.
    """
    if language == "German" and nlp is not None:
        word_info = await nlp.extract(word, sentence)
        if word_info is not None:
            lemma, related_words = resolve_lemma(word_info, word)
            level, stats = await _estimate_cefr(word, sentence, lemma, llm, model)
            logger.info("Lemma extracted (NLP)", extra={
                "word": word, "lemma": lemma,
                "related_words": related_words, "level": level,
            })
            return LemmaResult(
                lemma=lemma,
                related_words=related_words,
                level=level,
            ), stats
        # NLP failed — fall through to LLM path
        logger.info("NLP extraction failed, falling back to LLM",
                     extra={"word": word})

    return await _extract_with_llm(word, sentence, language, llm, model)


# ---------------------------------------------------------------------------
# Business rules (no external library access)
# ---------------------------------------------------------------------------

def resolve_lemma(info: dict[str, Any], original_word: str) -> tuple[str, list[str]]:
    """Determine lemma and related_words from extracted word info.

    Applies German grammar rules:
    - Articles (ART): lowercase text
    - Past-participle adjectives (ending in -en/-ern/-eln): lowercase text
    - Non-verbs: use NLP lemma directly
    - Verbs: combine base lemma with separable prefix and/or reflexive
    """
    if info["xpos"] == "ART":
        return info["text"].lower(), [original_word]

    if info["pos"] == "adj" and info["lemma"].endswith(("en", "ern", "eln")):
        return info["text"].lower(), [original_word]

    if info["pos"] != "verb":
        return info["lemma"], [original_word]

    # Verb: combine prefix + reflexive
    lemma = _combine_verb_lemma(info["lemma"], info["prefix"], info["reflexive"])
    return lemma, info["parts"]


def _combine_verb_lemma(
    base: str, prefix: str | None, reflexive: str | None,
) -> str:
    """Combine verb lemma with separable prefix and/or reflexive pronoun."""
    if reflexive:
        return f"sich {prefix}{base}" if prefix else f"sich {base}"
    if prefix:
        return f"{prefix}{base}"
    return base


# ---------------------------------------------------------------------------
# CEFR estimation (small LLM call for NLP path)
# ---------------------------------------------------------------------------

async def _estimate_cefr(
    word: str, sentence: str, lemma: str, llm: LLMPort, model: str,
) -> tuple[str | None, LLMCallResult | None]:
    """Estimate CEFR level with a minimal LLM call."""
    prompt = (
        f'Sentence: "{sentence}"\n'
        f'Word: "{word}", Lemma: "{lemma}"\n'
        f"CEFR level? Reply JSON only: {{\"level\": \"A1\"}}\n"
        f"A1=basic A2=daily B1=general B2=professional C1=academic C2=literary"
    )
    try:
        content, stats = await llm.call(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            max_tokens=_CEFR_PROMPT_MAX_TOKENS,
            temperature=0,
            timeout=10,
        )
        result = repair_json(content, return_objects=True)
        level = result.get("level") if isinstance(result, dict) else None
        return level, stats
    except Exception as e:
        logger.warning("CEFR estimation failed", extra={"error": str(e)})
        return None, None


# ---------------------------------------------------------------------------
# LLM extraction (non-German, or German fallback)
# ---------------------------------------------------------------------------

async def _extract_with_llm(
    word: str, sentence: str, language: str, llm: LLMPort, model: str,
) -> tuple[LemmaResult | None, LLMCallResult | None]:
    """Extract lemma using LLM reduced prompt."""
    try:
        prompt = _build_reduced_prompt(language, sentence, word)

        content, stats = await llm.call(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            max_tokens=_REDUCED_PROMPT_MAX_TOKENS,
            temperature=0,
        )

        parsed = repair_json(content, return_objects=True)
        if not isinstance(parsed, dict):
            logger.warning(
                "Failed to parse JSON from LLM reduced prompt",
                extra={"word": word, "language": language,
                        "content_preview": content[:200] if content else None},
            )
            return None, stats
        return LemmaResult(
            lemma=parsed.get("lemma", word),
            related_words=parsed.get("related_words"),
            level=parsed.get("level"),
        ), stats

    except Exception as e:
        logger.error(
            "Error in LLM reduced call",
            extra={"word": word, "language": language, "error": str(e)},
            exc_info=True,
        )
        return None, None


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

def _build_reduced_prompt(language: str, sentence: str, word: str) -> str:
    """Build reduced prompt by language."""
    if language == "English":
        return _build_reduced_prompt_en(sentence, word)
    if language == "German":
        return _build_reduced_prompt_de(sentence, word)
    return _build_reduced_prompt_generic(language, sentence, word)


def _build_reduced_prompt_de(sentence: str, word: str) -> str:
    """German reduced prompt for lemma extraction."""
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


def _build_reduced_prompt_en(sentence: str, word: str) -> str:
    """English reduced prompt for lemma extraction."""
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


def _build_reduced_prompt_generic(language: str, sentence: str, word: str) -> str:
    """Generic reduced prompt for other languages."""
    return f"""You are analyzing a {language} sentence to find the complete dictionary form of a clicked word.

Sentence: "{sentence}"
Clicked word: "{word}"

CRITICAL INSTRUCTIONS:
1. The clicked word may be part of a SEPARABLE VERB or COMPOUND WORD where parts are split across the sentence.
2. You MUST scan the ENTIRE sentence from start to end to find ALL parts that belong together with the clicked word.
3. Common patterns include separable verbs (verb stem + prefix/particle), compound words (base + prefix/suffix), and inflected forms (return the infinitive/base form).
4. The lemma MUST be the COMPLETE combined form as it appears in dictionaries, not just the clicked word or its stem.
5. If you find separated parts, combine them in the correct order (prefix + stem, or stem + particle).

Analyze the sentence structure carefully. Look for particles, prefixes, or other words that grammatically belong with "{word}".

IMPORTANT: If the word is part of a separable verb or compound word, identify ONLY the grammatical components that form the same lexical unit (lemma). Do NOT include prepositions, objects, or other words that are grammatically separate, even if they are semantically related.

Return ONLY valid JSON with these fields:
{{
  "lemma": "complete dictionary form with all parts combined",
  "related_words": ["list", "of", "all", "words", "in", "sentence", "belonging", "to", "this", "lemma"],
  "level": "CEFR level of this word (A1/A2/B1/B2/C1/C2)"
}}

IMPORTANT: related_words must contain ONLY the grammatical parts of the lemma (e.g., separable verb prefix + stem, reflexive pronoun for reflexive verbs). The order in related_words must match the exact order these words appear in the provided sentence: {sentence}."""
