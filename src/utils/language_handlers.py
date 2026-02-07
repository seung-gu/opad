"""Language-specific handlers for dictionary API processing.

Uses the Strategy Pattern to encapsulate language-specific logic for:
- Gender extraction from POS strings
- Gender extraction from sense tags
- Reflexive pronoun stripping
"""

from typing import Protocol


class LanguageHandler(Protocol):
    """Protocol defining language-specific processing methods."""

    @staticmethod
    def extract_gender_from_pos(pos: str) -> str | None:
        """Extract grammatical gender from part of speech string."""
        ...

    @staticmethod
    def extract_gender_from_tags(tags: list[str]) -> str | None:
        """Extract grammatical gender from sense tags."""
        ...

    @staticmethod
    def strip_reflexive_pronoun(word: str) -> str:
        """Strip reflexive pronouns from verb lemmas."""
        ...


class GermanHandler:
    """Handler for German language-specific processing."""

    @staticmethod
    def extract_gender_from_pos(pos: str) -> str | None:
        if not pos:
            return None
        pos_lower = pos.lower()
        if "masculine" in pos_lower or "männlich" in pos_lower:
            return "der"
        elif "feminine" in pos_lower or "weiblich" in pos_lower:
            return "die"
        elif "neuter" in pos_lower or "sächlich" in pos_lower:
            return "das"
        return None

    @staticmethod
    def extract_gender_from_tags(tags: list[str]) -> str | None:
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower == "masculine":
                return "der"
            elif tag_lower == "feminine":
                return "die"
            elif tag_lower == "neuter":
                return "das"
        return None

    @staticmethod
    def strip_reflexive_pronoun(word: str) -> str:
        reflexive_pronouns = ["sich ", "mich ", "dich ", "uns ", "euch "]
        word_lower = word.lower()
        for pronoun in reflexive_pronouns:
            if word_lower.startswith(pronoun):
                return word[len(pronoun):]
        return word


class FrenchHandler:
    """Handler for French language-specific processing."""

    @staticmethod
    def extract_gender_from_pos(pos: str) -> str | None:
        if not pos:
            return None
        pos_lower = pos.lower()
        if "masculine" in pos_lower or "masculin" in pos_lower:
            return "le"
        elif "feminine" in pos_lower or "féminin" in pos_lower:
            return "la"
        return None

    @staticmethod
    def extract_gender_from_tags(tags: list[str]) -> str | None:
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower in ("masculine", "masculin"):
                return "le"
            elif tag_lower in ("feminine", "féminin"):
                return "la"
        return None

    @staticmethod
    def strip_reflexive_pronoun(word: str) -> str:
        word_lower = word.lower()
        if word_lower.startswith("se "):
            return word[3:]
        elif word_lower.startswith("s'"):
            return word[2:]
        return word


class SpanishHandler:
    """Handler for Spanish language-specific processing."""

    @staticmethod
    def extract_gender_from_pos(pos: str) -> str | None:
        if not pos:
            return None
        pos_lower = pos.lower()
        if "masculine" in pos_lower or "masculino" in pos_lower:
            return "el"
        elif "feminine" in pos_lower or "femenino" in pos_lower:
            return "la"
        return None

    @staticmethod
    def extract_gender_from_tags(tags: list[str]) -> str | None:
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower in ("masculine", "masculino"):
                return "el"
            elif tag_lower in ("feminine", "femenino"):
                return "la"
        return None

    @staticmethod
    def strip_reflexive_pronoun(word: str) -> str:
        # Spanish reflexive verbs end in -arse, -erse, -irse
        # Only strip 'se' if preceded by a verb infinitive ending
        word_lower = word.lower()
        if word_lower.endswith("arse") or word_lower.endswith("erse") or word_lower.endswith("irse"):
            return word[:-2]
        return word


class DefaultHandler:
    """Default handler for languages without special processing."""

    @staticmethod
    def extract_gender_from_pos(pos: str) -> str | None:
        return None

    @staticmethod
    def extract_gender_from_tags(tags: list[str]) -> str | None:
        return None

    @staticmethod
    def strip_reflexive_pronoun(word: str) -> str:
        return word


# Language handler registry
LANGUAGE_HANDLERS: dict[str, type] = {
    "de": GermanHandler,
    "fr": FrenchHandler,
    "es": SpanishHandler,
}


def get_language_handler(language_code: str) -> type:
    """Get the appropriate language handler for a language code.

    Args:
        language_code: ISO 639-1 language code (e.g., "de", "fr", "es").

    Returns:
        Language handler class.
    """
    return LANGUAGE_HANDLERS.get(language_code, DefaultHandler)
