"""Prompt templates for full LLM fallback.

Reduced prompts (lemma extraction) have moved to utils.lemma_extraction.
Sense selection prompts have moved to utils.sense_selection.
"""


def build_word_definition_prompt(language: str, sentence: str, word: str) -> str:
    """Build prompt for extracting word definition and lemma. (Full LLM fallback)

    This prompt is designed to help LLMs identify:
    - Complete lemma forms (especially for separable verbs in German)
    - Context-aware definitions
    - Compound words with split parts

    Args:
        language: Language of the sentence (e.g., "German", "English")
        sentence: Full sentence containing the word
        word: Clicked word to define

    Returns:
        Formatted prompt string ready for LLM
    """
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
