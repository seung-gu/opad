"""Lemma extraction module — Step 1 of the dictionary lookup pipeline.

Extracts lemma + related_words + CEFR level from a word in context.
German uses Stanza NLP (local, ~51ms); other languages use LLM (~800ms).
Both paths return the same dict format: {"lemma", "related_words", "level"}.
"""

import asyncio
import logging
import threading
from typing import Any

from utils.llm import TokenUsageStats, call_llm_with_tracking, parse_json_from_content

logger = logging.getLogger(__name__)

# Token limits
_REDUCED_PROMPT_MAX_TOKENS = 200
_CEFR_PROMPT_MAX_TOKENS = 10

# ---------------------------------------------------------------------------
# Stanza singleton
# ---------------------------------------------------------------------------
_stanza_pipeline = None
_stanza_lock = threading.Lock()


def _get_stanza_pipeline():
    """Lazy-load Stanza German pipeline (singleton, ~349MB). Thread-safe."""
    global _stanza_pipeline
    if _stanza_pipeline is None:
        with _stanza_lock:
            if _stanza_pipeline is None:  # Double-check after acquiring lock
                import stanza
                _stanza_pipeline = stanza.Pipeline(
                    "de",
                    processors="tokenize,mwt,pos,lemma,depparse",
                    logging_level="WARN",
                )
                logger.info("Stanza German pipeline loaded")
    return _stanza_pipeline


def preload_stanza() -> None:
    """Eagerly load Stanza pipeline (call at service startup)."""
    _get_stanza_pipeline()


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

async def extract_lemma(
    word: str,
    sentence: str,
    language: str,
    model: str = "openai/gpt-4.1-mini",
) -> tuple[dict[str, Any] | None, TokenUsageStats | None]:
    """Extract lemma, related_words, and CEFR level for a word in context.

    German uses Stanza NLP with a small LLM call for CEFR.
    Other languages use LLM reduced prompt.

    Args:
        word: The clicked word.
        sentence: Full sentence containing the word.
        language: Language name (e.g., "German", "English").
        model: LLM model identifier for reduced prompt / CEFR calls.

    Returns:
        Tuple of (result_dict, token_stats).
        result_dict has keys: "lemma", "related_words", "level".
        Returns (None, None) on failure.
    """
    if language == "German":
        result = await _extract_with_stanza(word, sentence)
        if result is not None:
            # Stanza doesn't know CEFR — ask LLM with a tiny prompt
            level, stats = await _estimate_cefr(
                word, sentence, result["lemma"], model
            )
            result["level"] = level
            logger.info("Lemma extracted (Stanza)", extra={
                "word": word, "lemma": result["lemma"],
                "related_words": result["related_words"],
                "level": level,
            })
            return result, stats
        # Stanza failed — fall through to LLM path
        logger.info("Stanza extraction failed, falling back to LLM",
                     extra={"word": word})

    return await _extract_with_llm(word, sentence, language, model)


# ---------------------------------------------------------------------------
# Stanza extraction (German)
# ---------------------------------------------------------------------------

async def _extract_with_stanza(word: str, sentence: str) -> dict[str, Any] | None:
    """Extract lemma + related_words using Stanza dependency parsing.

    Runs the pipeline in a thread to avoid blocking the event loop.

    Returns:
        {"lemma": str, "related_words": list[str]} or None on failure.
    """
    try:
        pipeline = _get_stanza_pipeline()
        doc = await asyncio.to_thread(pipeline, sentence)
    except Exception as e:
        logger.warning("Stanza pipeline error", extra={"error": str(e)})
        return None

    # Find the target token (returns token and its sentence)
    target, target_sent = _find_target_token(doc, word)
    if target is None:
        return None

    # Build lemma and related_words from dependency tree
    lemma, related_words = _build_lemma_from_dep_tree(target_sent, target, word)
    return {"lemma": lemma, "related_words": related_words}


def _find_target_token(doc, word: str) -> tuple[Any, Any]:
    """Find the Stanza token matching the clicked word.

    Returns:
        Tuple of (token, sentence) or (None, None) if not found.
    """
    for sent in doc.sentences:
        for token in sent.words:
            if token.text == word:
                return token, sent
    # Case-insensitive fallback
    word_lower = word.lower()
    for sent in doc.sentences:
        for token in sent.words:
            if token.text.lower() == word_lower:
                return token, sent
    return None, None


def _build_lemma_from_dep_tree(sent, target, word: str) -> tuple[str, list[str]]:
    """Build lemma and related_words from Stanza dependency tree.

    Handles: separable verbs (compound:prt), reflexive verbs (sich),
    articles (ART normalization), past-participle adjectives.

    Args:
        sent: The Stanza sentence containing the target token.
        target: The target Stanza token.
        word: The original clicked word.

    Returns:
        Tuple of (lemma_string, related_words_list).
    """
    # Non-verb early returns
    if target.xpos == "ART":
        return target.text.lower(), [word]
    if target.upos == "ADJ" and target.lemma.endswith(("en", "ern", "eln")):
        return target.text.lower(), [word]
    if target.upos != "VERB":
        return target.lemma, [word]

    # --- Verb handling ---
    prefix_text = _find_dep_child(sent, target.id, deprel="compound:prt")
    reflexive_text = _find_dep_child(sent, target.id, xpos="PRF")

    base_lemma = _combine_verb_lemma(target.lemma, prefix_text, reflexive_text)
    related = _collect_related_words(sent, target, word)
    return base_lemma, related


def _find_dep_child(sent, head_id: int, *, deprel: str | None = None, xpos: str | None = None) -> str | None:
    """Find first child token matching deprel or xpos."""
    for w in sent.words:
        if w.head == head_id:
            if deprel and w.deprel == deprel:
                return w.text
            if xpos and w.xpos == xpos:
                return w.text
    return None


def _combine_verb_lemma(base: str, prefix: str | None, reflexive: str | None) -> str:
    """Combine verb lemma with prefix and/or reflexive pronoun."""
    if reflexive:
        return f"sich {prefix}{base}" if prefix else f"sich {base}"
    if prefix:
        return f"{prefix}{base}"
    return base


def _collect_related_words(sent, target, word: str) -> list[str]:
    """Collect related words (verb + prefix + reflexive) sorted by position."""
    parts = []
    for w in sent.words:
        if w.id == target.id:
            parts.append((w.id, w.text))
        elif w.head == target.id and w.deprel == "compound:prt":
            parts.append((w.id, w.text))
        elif w.head == target.id and w.xpos == "PRF":
            parts.append((w.id, w.text))

    parts.sort(key=lambda x: x[0])
    related = [text for _, text in parts]
    return related if related else [word]


# ---------------------------------------------------------------------------
# CEFR estimation (small LLM call for Stanza path)
# ---------------------------------------------------------------------------

async def _estimate_cefr(
    word: str, sentence: str, lemma: str, model: str,
) -> tuple[str | None, TokenUsageStats | None]:
    """Estimate CEFR level with a minimal LLM call."""
    prompt = (
        f'Sentence: "{sentence}"\n'
        f'Word: "{word}", Lemma: "{lemma}"\n'
        f"CEFR level? Reply JSON only: {{\"level\": \"A1\"}}\n"
        f"A1=basic A2=daily B1=general B2=professional C1=academic C2=literary"
    )
    try:
        content, stats = await call_llm_with_tracking(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            max_tokens=_CEFR_PROMPT_MAX_TOKENS,
            temperature=0,
            timeout=10,
        )
        result = parse_json_from_content(content)
        level = result.get("level") if result else None
        return level, stats
    except Exception as e:
        logger.warning("CEFR estimation failed", extra={"error": str(e)})
        return None, None


# ---------------------------------------------------------------------------
# LLM extraction (non-German, or German fallback)
# ---------------------------------------------------------------------------

async def _extract_with_llm(
    word: str, sentence: str, language: str, model: str,
) -> tuple[dict[str, Any] | None, TokenUsageStats | None]:
    """Extract lemma using LLM reduced prompt."""
    try:
        prompt = _build_reduced_prompt(language, sentence, word)

        content, stats = await call_llm_with_tracking(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            max_tokens=_REDUCED_PROMPT_MAX_TOKENS,
            temperature=0,
        )

        result = parse_json_from_content(content)
        if result is None:
            logger.warning(
                "Failed to parse JSON from LLM reduced prompt",
                extra={"word": word, "language": language,
                        "content_preview": content[:200] if content else None},
            )
        return result, stats

    except Exception as e:
        logger.error(
            "Error in LLM reduced call",
            extra={"word": word, "language": language, "error": str(e)},
            exc_info=True,
        )
        return None, None


# ---------------------------------------------------------------------------
# Prompt templates (moved from prompts.py)
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
