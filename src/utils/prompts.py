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
  "lemma": "complete dictionary form with all parts combined",
  "definition": "meaning in this sentence context",
  "related_words": ["list", "of", "all", "words", "in", "sentence", "belonging", "to", "this", "lemma"]
}}

IMPORTANT: related_words must contain ONLY the grammatical parts of the lemma (e.g., separable verb prefix + stem, reflexive pronoun for reflexive verbs). The order in related_words must match the exact order these words appear in the provided sentence :{sentence}."""
    if language == "German":
        prompt += """
        
IMPORTANT for German language:
1. Separable verbs (trennbare Verben): 
   - Common prefixes: ab-, an-, auf-, aus-, ein-, fest-, fort-, hin-, los-, mit-, nach-, 
     über-, um-, unter-, vor-, weg-, weiter-, zu-, zurück-, zusammen-, etc.
   - If the clicked word is a verb conjugation (findet, fand, finde, etc.), ALWAYS scan 
     the ENTIRE sentence for the separated prefix that belongs to it.
   - Examples: "findet statt" → lemma="stattfinden", related_words=["findet", "statt"]
   - Example: "haben ... gefunden" → lemma="finden", related_words=["haben", "gefunden"]
   - The lemma must include the complete separable prefix combined with the stem.

2. Reflexive verbs (reflexive Verben): 
   - If the clicked word is part of a reflexive verb, include "sich" in the related_words array.
   - Example: "sich erinnert" → lemma="sich erinnern", related_words=["sich", "erinnert"]
   - The lemma should be the complete reflexive form with "sich".

3. Prepositional verbs (Präpositionalverben): 
   - If the verb requires a specific preposition (e.g., "auf", "mit", "von", "an", "für"), 
     include that preposition in the related_words array.
   - Example: "wartet auf" → lemma="warten auf", related_words=["wartet", "auf"]

CRITICAL: For ALL these cases, regardless of which word the user clicked, scan the ENTIRE 
sentence to find ALL words that belong to the same lexical unit and include them in related_words 
in the order they appear in the sentence.
        """
    return prompt
