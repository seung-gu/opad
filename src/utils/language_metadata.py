"""Language-specific metadata for dictionary API processing.

Pure data module — no logic, only constants.
Each pipeline step owns its logic and references this data as needed.
"""

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
