"""Stanza NLP adapter — extracts linguistic information from German text.

Implements NLPPort by wrapping the Stanza library. All Stanza-specific
types (Document, Sentence, Word) are confined within this adapter;
only primitive dicts cross the boundary.
"""

import asyncio
import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)

# Stanza feats Gender value → German article
_GENDER_ARTICLE_MAP = {
    "Masc": "der",
    "Fem": "die",
    "Neut": "das",
}


class StanzaAdapter:
    """Adapter that extracts linguistic info using Stanza NLP pipeline.

    Thread-safe singleton pipeline: loaded once, reused across requests.
    The pipeline runs synchronously (~50ms), so extract() offloads it
    to a thread to avoid blocking the event loop.
    """

    def __init__(self):
        self._pipeline = None
        self._lock = threading.Lock()

    def preload(self) -> None:
        """Eagerly load the Stanza pipeline (call at service startup)."""
        self._ensure_pipeline()

    # ------------------------------------------------------------------
    # Public interface (implements NLPPort)
    # ------------------------------------------------------------------

    async def extract(self, word: str, sentence: str) -> dict[str, Any] | None:
        """Extract linguistic info for a word in a German sentence.

        Returns:
            Dict with keys: text, lemma, pos, xpos, gender,
            prefix, reflexive, parts.  Or None on failure.
        """
        try:
            pipeline = self._ensure_pipeline()
            parsed = await asyncio.to_thread(pipeline, sentence)
        except Exception as e:
            logger.warning("Stanza pipeline error", extra={"error": str(e)})
            return None

        word_token, matched_sentence = self._match_word(parsed, word)
        if word_token is None:
            return None

        return self._read_word_info(matched_sentence, word_token)

    # ------------------------------------------------------------------
    # Pipeline management
    # ------------------------------------------------------------------

    def _ensure_pipeline(self):
        """Lazy-load Stanza German pipeline (singleton, thread-safe)."""
        if self._pipeline is None:
            with self._lock:
                if self._pipeline is None:
                    import stanza

                    self._pipeline = stanza.Pipeline(
                        "de",
                        processors="tokenize,mwt,pos,lemma,depparse",
                        logging_level="WARN",
                    )
                    logger.info("Stanza German pipeline loaded")
        return self._pipeline

    # ------------------------------------------------------------------
    # Word matching
    # ------------------------------------------------------------------

    def _match_word(self, parsed, word: str) -> tuple[Any, Any]:
        """Find the token in parsed output matching the clicked word.

        Tries exact match first, then case-insensitive fallback.
        Returns (word_token, sentence) or (None, None).
        """
        for sentence in parsed.sentences:
            for token in sentence.words:
                if token.text == word:
                    return token, sentence

        word_lower = word.lower()
        for sentence in parsed.sentences:
            for token in sentence.words:
                if token.text.lower() == word_lower:
                    return token, sentence

        return None, None

    # ------------------------------------------------------------------
    # Info extraction (reads from Stanza objects → primitives)
    # ------------------------------------------------------------------

    def _read_word_info(self, sentence, word_token) -> dict[str, Any]:
        """Read all linguistic attributes from a matched word token."""
        return {
            "text": word_token.text,
            "lemma": word_token.lemma,
            "pos": word_token.upos.lower() if word_token.upos else None,
            "xpos": word_token.xpos,
            "gender": self._read_gender(word_token),
            "prefix": self._child_text(
                sentence, word_token.id, relation="compound:prt",
            ),
            "reflexive": self._child_text(
                sentence, word_token.id, xpos="PRF",
            ),
            "parts": self._collect_parts(sentence, word_token),
        }

    def _read_gender(self, word_token) -> str | None:
        """Extract grammatical gender from morphological features.

        Parses feats string like 'Case=Nom|Gender=Masc|Number=Sing'.
        """
        feats = getattr(word_token, "feats", None)
        if not feats:
            return None
        for feat in feats.split("|"):
            if feat.startswith("Gender="):
                gender_value = feat.split("=", 1)[1]
                return _GENDER_ARTICLE_MAP.get(gender_value)
        return None

    def _child_text(
        self,
        sentence,
        head_id: int,
        *,
        relation: str | None = None,
        xpos: str | None = None,
    ) -> str | None:
        """Find the text of a dependent matching relation or xpos."""
        for w in sentence.words:
            if w.head == head_id:
                if relation and w.deprel == relation:
                    return w.text
                if xpos and w.xpos == xpos:
                    return w.text
        return None

    def _collect_parts(self, sentence, word_token) -> list[str]:
        """Collect the word and its verb-related dependents, sorted by position.

        Includes: the word itself, separable prefix (compound:prt),
        reflexive pronoun (PRF).
        """
        parts: list[tuple[int, str]] = []
        for w in sentence.words:
            is_self = w.id == word_token.id
            is_dependent = w.head == word_token.id and (
                w.deprel == "compound:prt" or w.xpos == "PRF"
            )
            if is_self or is_dependent:
                parts.append((w.id, w.text))

        parts.sort(key=lambda x: x[0])
        return [text for _, text in parts] if parts else [word_token.text]
