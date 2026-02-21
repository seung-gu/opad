"""Dictionary lookup service — orchestrates the hybrid lookup pipeline.

Pipeline: Step 1 (lemma extraction) → Dictionary API → Step 2 (sense selection)
Falls back to full LLM when the hybrid pipeline fails.
Token usage is tracked per LLM call via token_usage_service.
"""

import logging

from domain.model.vocabulary import GrammaticalInfo, LookupResult
from port.dictionary import DictionaryPort
from port.llm import LLMPort
from port.nlp import NLPPort
from port.token_usage_repository import TokenUsageRepository
from services.token_usage_service import track_llm_usage
from json_repair import repair_json
from services.lemma_extraction import LemmaResult, extract_lemma
from services.sense_selection import select_best_sense

logger = logging.getLogger(__name__)

# Token limits for full LLM fallback
FULL_PROMPT_MAX_TOKENS = 2000

# Default messages
DEFAULT_DEFINITION = "Definition not found"


async def lookup(
    word: str,
    sentence: str,
    language: str,
    dictionary: DictionaryPort,
    llm: LLMPort,
    nlp: NLPPort | None = None,
    token_usage_repo: TokenUsageRepository | None = None,
    user_id: str | None = None,
    article_id: str | None = None,
    reduced_llm_model: str = "openai/gpt-4.1-mini",
    full_llm_model: str = "openai/gpt-4.1-mini",
) -> LookupResult:
    """Perform dictionary lookup using hybrid approach.

    Falls back to full LLM when hybrid pipeline fails.
    Token usage is tracked per LLM call if token_usage_repo is provided.
    """
    hybrid_result = await _perform_hybrid_lookup(
        word, sentence, language, dictionary, llm, nlp,
        reduced_llm_model, full_llm_model,
        token_usage_repo, user_id, article_id,
    )
    if hybrid_result is not None:
        return hybrid_result
    return await _fallback_full_llm(
        word, sentence, language, llm, full_llm_model,
        token_usage_repo, user_id, article_id,
    )


# ------------------------------------------------------------------
# Hybrid pipeline
# ------------------------------------------------------------------

async def _perform_hybrid_lookup(
    word: str,
    sentence: str,
    language: str,
    dictionary: DictionaryPort,
    llm: LLMPort,
    nlp: NLPPort | None,
    reduced_llm_model: str,
    full_llm_model: str,
    token_usage_repo: TokenUsageRepository | None,
    user_id: str | None,
    article_id: str | None,
) -> LookupResult | None:
    """Execute the hybrid pipeline: lemma → API → sense selection."""
    # Step 1: Lemma extraction
    lemma_data, lemma_stats = await extract_lemma(
        word, sentence, language, llm, nlp=nlp, model=reduced_llm_model,
    )
    if lemma_data is None:
        return None

    # Track lemma extraction usage
    if token_usage_repo and user_id:
        track_llm_usage(
            token_usage_repo, lemma_stats, user_id,
            operation="dictionary_search",
            article_id=article_id,
            metadata={"word": word, "language": language, "step": "lemma_extraction"},
        )

    lemma = lemma_data["lemma"]
    logger.info("Lemma extracted", extra={
        "word": word, "lemma": lemma,
        "related_words": lemma_data["related_words"],
        "level": lemma_data["level"],
    })

    # Step 2: Dictionary API
    entries = await dictionary.fetch(word=lemma, language=language)
    if not entries:
        logger.info("Dictionary API unavailable, falling back to full LLM",
                     extra={"word": word, "lemma": lemma})
        return None

    # Step 3: Sense selection
    sense, sense_label, sense_stats = await select_best_sense(
        sentence, word, entries, dictionary, llm, model=full_llm_model,
    )

    # Track sense selection usage
    if token_usage_repo and user_id:
        track_llm_usage(
            token_usage_repo, sense_stats, user_id,
            operation="dictionary_search",
            article_id=article_id,
            metadata={"word": word, "language": language, "step": "sense_selection"},
        )

    # Extract grammar via port
    grammar = dictionary.extract_grammar(entries, sense_label, language)

    # Build final result
    result = _build_result(lemma_data, grammar, sense)

    logger.info("Word definition extracted (hybrid)", extra={
        "word": word, "lemma": result.lemma,
        "related_words": result.related_words,
        "pos": result.grammar.pos,
        "gender": result.grammar.gender,
        "level": result.level,
        "language": language,
    })
    return result


# ------------------------------------------------------------------
# Full LLM fallback
# ------------------------------------------------------------------

async def _fallback_full_llm(
    word: str,
    sentence: str,
    language: str,
    llm: LLMPort,
    full_llm_model: str,
    token_usage_repo: TokenUsageRepository | None,
    user_id: str | None,
    article_id: str | None,
) -> LookupResult:
    """Fallback to full LLM when hybrid pipeline fails."""
    prompt = _build_full_prompt(
        language=language, sentence=sentence, word=word,
    )

    content, stats = await llm.call(
        messages=[{"role": "user", "content": prompt}],
        model=full_llm_model,
        max_tokens=FULL_PROMPT_MAX_TOKENS,
        temperature=0,
    )

    # Track full LLM fallback usage
    if token_usage_repo and user_id:
        track_llm_usage(
            token_usage_repo, stats, user_id,
            operation="dictionary_search",
            article_id=article_id,
            metadata={"word": word, "step": "full_llm_fallback"},
        )

    result = repair_json(content, return_objects=True)
    if isinstance(result, dict):
        logger.info("Word definition extracted (full LLM fallback)", extra={
            "word": word, "lemma": result.get("lemma", word),
            "language": language,
        })
        return LookupResult(
            lemma=result.get("lemma", word),
            definition=result.get("definition", DEFAULT_DEFINITION),
            related_words=result.get("related_words"),
            level=result.get("level"),
            grammar=GrammaticalInfo(
                pos=result.get("pos"),
                gender=result.get("gender"),
                conjugations=result.get("conjugations"),
            ),
        )

    logger.warning("Failed to parse JSON in fallback", extra={
        "word": word, "content_preview": content[:200] if content else None,
    })
    return LookupResult(
        lemma=word,
        definition=DEFAULT_DEFINITION,
    )


# ------------------------------------------------------------------
# Result building helpers
# ------------------------------------------------------------------

def _build_result(
    lemma_data: LemmaResult,
    grammar: GrammaticalInfo,
    sense,
) -> LookupResult:
    """Merge lemma extraction, API metadata, and sense selection into LookupResult."""
    return LookupResult(
        lemma=lemma_data["lemma"],
        definition=sense.definition or DEFAULT_DEFINITION,
        related_words=lemma_data["related_words"],
        level=lemma_data["level"],
        grammar=GrammaticalInfo(
            pos=grammar.pos,
            gender=grammar.gender,
            phonetics=grammar.phonetics,
            conjugations=grammar.conjugations,
            examples=sense.examples,
        ),
    )


def _build_full_prompt(language: str, sentence: str, word: str) -> str:
    """Build prompt for full LLM fallback — extracts lemma, definition, grammar."""
    prompt = f"""You are analyzing a {language} sentence to find the complete dictionary form of a clicked word.

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

Return ONLY valid JSON:
{{
  "lemma": "complete dictionary form (nouns: WITHOUT article, e.g. 'Rennfahren' not 'das Rennfahren')",
  "definition": "meaning in this sentence context",
  "related_words": ["only grammatical parts of the lemma from the sentence, NOT articles (der/die/das/dem/den/ein/eine)"],
  "pos": "part of speech (noun/verb/adjective/adverb/preposition/conjunction/etc)",
  "gender": "grammatical gender if applicable (der/die/das for German, le/la for French, el/la for Spanish nouns). Use null if not applicable.",
  "conjugations": {{
    "present": "3rd person singular present (for verbs only, null for non-verbs)",
    "past": "3rd person singular past/preterite (for verbs only, null for non-verbs)",
    "participle": "past participle (for verbs only, null for non-verbs)",
    "auxiliary": "haben or sein (for German verbs only, null otherwise)",
    "genitive": "genitive form (for nouns only, null for non-nouns)",
    "plural": "plural form (for nouns only, null for non-nouns)"
  }},
  "level": "CEFR level of this word (A1/A2/B1/B2/C1/C2)"
}}

IMPORTANT: related_words must contain ONLY the grammatical parts of the lemma (e.g., separable verb prefix + stem, reflexive pronoun for reflexive verbs). The order in related_words must match the exact order these words appear in the provided sentence: {sentence}."""
    if language == "German":
        prompt += """

IMPORTANT for German language:
1. Separable verbs (trennbare Verben): If the clicked word is part of a separable verb with separable prefixes (ab-, aus-, ein-, mit-, vor-, etc.), identify ALL components including the prefix and any associated prepositions. The lemma must include the complete separable prefix.
2. Reflexive verbs (reflexive Verben): If the clicked word is part of a reflexive verb construction requiring "sich", include "sich" in the related_words array. The lemma should be the complete reflexive form.
3. Prepositional verbs (Präpositionalverben): If the verb requires a specific preposition (e.g., "von", "mit", "auf"), include that preposition in the related_words array.

For all these cases, scan the ENTIRE sentence to find ALL words that belong to the same lexical unit and include them in related_words.
        """
    return prompt