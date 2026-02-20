"""NLP port — outbound interface for natural language processing."""

from typing import Protocol


class NLPPort(Protocol):
    """Port for extracting linguistic information from text.

    Implementations wrap NLP libraries (e.g., Stanza, spaCy) and return
    extracted word information as primitive dicts — no library-specific
    types leak through this boundary.

    Returned dict keys:
        text, lemma, pos, xpos, gender, prefix, reflexive, parts
    """

    async def extract(self, word: str, sentence: str) -> dict | None:
        """Extract linguistic info for a word in context.

        Args:
            word: The clicked word to analyze.
            sentence: Full sentence containing the word.

        Returns:
            Dict with extracted primitives, or None on failure.
        """
        ...
