"""Language Value Object.

Encapsulates language-specific metadata used across the domain:
language codes, gender articles, and reflexive pronoun patterns.
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class Language:
    """Immutable value object representing a supported language."""

    name: str
    code: str
    gender_articles: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    reflexive_prefixes: tuple[str, ...] = ()
    reflexive_suffixes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        # Freeze mutable dict passed at construction time
        if isinstance(self.gender_articles, dict):
            object.__setattr__(self, "gender_articles", MappingProxyType(self.gender_articles))

    def strip_reflexive(self, word: str) -> str:
        """Strip reflexive pronouns from a verb lemma for API lookup.

        Handles prefix-style reflexives (e.g., "sich gewöhnen" → "gewöhnen")
        and suffix-style reflexives (e.g., "levantarse" → "levantar").

        Args:
            word: The word to strip reflexive pronoun from.

        Returns:
            The word with reflexive pronoun removed, or unchanged if none found.
        """
        word_lower = word.lower()
        for prefix in self.reflexive_prefixes:
            if word_lower.startswith(prefix):
                return word[len(prefix):]
        for suffix in self.reflexive_suffixes:
            if word_lower.endswith(suffix):
                # Strip "se" (2 chars) — Spanish reflexive endings (arse/erse/irse)
                return word[:-2]
        return word


# ── Language instances ────────────────────────────────────────

GERMAN = Language(
    name="German",
    code="de",
    gender_articles={
        "masculine": "der", "männlich": "der",
        "feminine": "die", "weiblich": "die",
        "neuter": "das", "sächlich": "das",
    },
    reflexive_prefixes=("sich ", "mich ", "dich ", "uns ", "euch "),
    reflexive_suffixes=(),
)

ENGLISH = Language(
    name="English",
    code="en",
    gender_articles={},
    reflexive_prefixes=(),
    reflexive_suffixes=(),
)

FRENCH = Language(
    name="French",
    code="fr",
    gender_articles={
        "masculine": "le", "masculin": "le",
        "feminine": "la", "féminin": "la",
    },
    reflexive_prefixes=("se ", "s'"),
    reflexive_suffixes=(),
)

SPANISH = Language(
    name="Spanish",
    code="es",
    gender_articles={
        "masculine": "el", "masculino": "el",
        "feminine": "la", "femenino": "la",
    },
    reflexive_prefixes=(),
    reflexive_suffixes=("arse", "erse", "irse"),
)

ITALIAN = Language(
    name="Italian",
    code="it",
    gender_articles={},
    reflexive_prefixes=(),
    reflexive_suffixes=(),
)

KOREAN = Language(
    name="Korean",
    code="ko",
    gender_articles={},
    reflexive_prefixes=(),
    reflexive_suffixes=(),
)


# ── Registry ──────────────────────────────────────────────────

LANGUAGES: dict[str, Language] = {
    lang.name: lang
    for lang in (
        GERMAN, ENGLISH, FRENCH, SPANISH, ITALIAN, KOREAN,
    )
}


def get_language(name: str) -> Language | None:
    """Look up a Language by its full name (e.g., "German").

    Returns None for unsupported or unknown language names.
    """
    return LANGUAGES.get(name)
