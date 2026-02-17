"""Language-specific metadata for dictionary and NLP processing.

Provides language code mapping and constants used by adapters and services.
"""

# Map full language names to ISO 639-1 codes
LANGUAGE_CODE_MAP: dict[str, str] = {
    "German": "de",
    "English": "en",
    "French": "fr",
    "Spanish": "es",
    "Italian": "it",
    "Portuguese": "pt",
    "Dutch": "nl",
    "Polish": "pl",
    "Russian": "ru",
}


def get_language_code(language: str) -> str | None:
    """Convert full language name to ISO 639-1 code."""
    return LANGUAGE_CODE_MAP.get(language)


# Gender keyword → article mapping per language
# Keys are lowercased for case-insensitive matching
GENDER_MAP: dict[str, dict[str, str]] = {
    "de": {
        "masculine": "der", "männlich": "der",
        "feminine": "die", "weiblich": "die",
        "neuter": "das", "sächlich": "das",
    },
    "fr": {
        "masculine": "le", "masculin": "le",
        "feminine": "la", "féminin": "la",
    },
    "es": {
        "masculine": "el", "masculino": "el",
        "feminine": "la", "femenino": "la",
    },
}

# Reflexive pronoun prefixes to strip (lowercased)
REFLEXIVE_PREFIXES: dict[str, list[str]] = {
    "de": ["sich ", "mich ", "dich ", "uns ", "euch "],
    "fr": ["se ", "s'"],
}

# Reflexive verb suffix patterns (Spanish: levantarse → levantar)
# If word ends with suffix, strip last 2 chars ("se")
REFLEXIVE_SUFFIXES: dict[str, list[str]] = {
    "es": ["arse", "erse", "irse"],
}

# Languages that support IPA phonetics from Free Dictionary API
PHONETICS_SUPPORTED: set[str] = {"en"}
