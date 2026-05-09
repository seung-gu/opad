"""Stanza NLP adapter — extracts linguistic information from German text.

Implements NLPPort by wrapping the Stanza library. All Stanza-specific
types (Document, Sentence, Word) are confined within this adapter;
only primitive dicts cross the boundary.
"""

import asyncio
import logging
import os
import threading
from typing import Any

logger = logging.getLogger(__name__)

# Stanza feats Gender value → German article
_GENDER_ARTICLE_MAP = {
    "Masc": "der",
    "Fem": "die",
    "Neut": "das",
}


_IDLE_TTL_SECONDS = int(os.getenv("STANZA_IDLE_TTL_MIN", "60")) * 60


class StanzaAdapter:
    """Adapter that extracts linguistic info using Stanza NLP pipeline.

    Thread-safe singleton pipeline: loaded on first use, reused across requests.
    Automatically unloads after idle timeout to reclaim ~800MB memory.
    The pipeline runs synchronously (~50ms), so extract() offloads it
    to a thread to avoid blocking the event loop.
    """

    def __init__(self):
        self._pipeline = None
        self._lock = threading.Lock()
        self._unload_timer: asyncio.TimerHandle | None = None

    def preload(self) -> None:
        """Import stanza at startup to avoid memory fragmentation later (~400MB)."""
        import stanza  # noqa: F401
        logger.info("Stanza module imported (preload)")

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
            self._schedule_unload()
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

    def _schedule_unload(self) -> None:
        """Schedule pipeline unload after idle timeout. Resets on each call."""
        if self._unload_timer:
            self._unload_timer.cancel()
        try:
            loop = asyncio.get_event_loop()
            self._unload_timer = loop.call_later(
                _IDLE_TTL_SECONDS, self._unload_pipeline,
            )
        except RuntimeError:
            pass  # No event loop (e.g. testing)

    def _unload_pipeline(self) -> None:
        """Unload pipeline to reclaim ~800MB memory."""
        with self._lock:
            self._pipeline = None
            self._unload_timer = None
        import gc
        gc.collect()
        try:
            import ctypes
            ctypes.CDLL("libc.so.6").malloc_trim(0)
        except OSError:
            pass  # macOS — no libc.so.6
        logger.info("Stanza pipeline unloaded (idle %dm)", _IDLE_TTL_SECONDS // 60)

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
