"""Prompt templates for LLM interactions."""


def build_word_definition_prompt(language: str, sentence: str, word: str) -> str:
    """Build prompt for extracting word definition and lemma.
    
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

Return ONLY valid JSON:
{{
  "lemma": "complete dictionary form with all parts combined",
  "definition": "meaning in this sentence context"
}}"""
