"""Prompt templates for LLM interactions."""


def build_reduced_prompt_de(sentence: str, word: str) -> str:
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


def build_reduced_prompt_en(sentence: str, word: str) -> str:
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


def build_reduced_word_definition_prompt(language: str, sentence: str, word: str) -> str:
    """Build reduced prompt for hybrid dictionary lookup.

    This prompt requests only lemma, related_words, and CEFR level from the LLM.
    Other fields (definition, pos, phonetics, forms) are obtained from
    the Free Dictionary API in the hybrid approach.

    Args:
        language: Language of the sentence (e.g., "German", "English").
        sentence: Full sentence containing the word.
        word: Clicked word to define.

    Returns:
        Formatted prompt string ready for LLM.
    """
    if language == "English":
        return build_reduced_prompt_en(sentence, word)
    elif language == "German":
        return build_reduced_prompt_de(sentence, word)
    
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

Return ONLY valid JSON with these fields:
{{
  "lemma": "complete dictionary form with all parts combined",
  "related_words": ["list", "of", "all", "words", "in", "sentence", "belonging", "to", "this", "lemma"],
  "level": "CEFR level of this word (A1/A2/B1/B2/C1/C2)"
}}

IMPORTANT: related_words must contain ONLY the grammatical parts of the lemma (e.g., separable verb prefix + stem, reflexive pronoun for reflexive verbs). The order in related_words must match the exact order these words appear in the provided sentence: {sentence}."""

    return prompt


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
