"""In-memory implementation of DictionaryPort for testing."""

from typing import Any

from domain.model.vocabulary import GrammaticalInfo, SenseResult


class FakeDictionaryAdapter:
    """Fake dictionary adapter that returns preconfigured responses."""

    def __init__(self, entries: list[dict] | None = None):
        self.entries = entries
        self.last_word: str | None = None
        self.last_language: str | None = None

    async def fetch(self, word: str, language: str) -> list[dict] | None:
        self.last_word = word
        self.last_language = language
        return self.entries

    def build_sense_listing(self, entries: list[dict[str, Any]]) -> str | None:
        if len(entries) == 1:
            senses = entries[0].get("senses", [])
            if len(senses) <= 1 and not (senses and senses[0].get("subsenses")):
                return None
        lines = []
        for i, entry in enumerate(entries):
            pos = entry.get("partOfSpeech", "unknown")
            lines.append(f"entries[{i}] ({pos}):")
            for j, sense in enumerate(entry.get("senses", [])):
                lines.append(f"  {i}.{j} {sense.get('definition', '')}")
        return "\n".join(lines)

    def get_sense(
        self, entries: list[dict[str, Any]], label: str,
    ) -> SenseResult:
        parts = label.split(".")
        ei = int(parts[0]) if parts else 0
        si = int(parts[1]) if len(parts) > 1 else 0
        ei = max(0, min(ei, len(entries) - 1))
        senses = entries[ei].get("senses", [])
        si = max(0, min(si, len(senses) - 1)) if senses else 0
        if not senses or si >= len(senses):
            return SenseResult()
        sense = senses[si]
        definition = sense.get("definition", "")
        raw_examples = sense.get("examples", [])[:3]
        examples = [
            e if isinstance(e, str) else e.get("text", "")
            for e in raw_examples
        ] or None
        return SenseResult(definition=definition, examples=examples)

    def extract_grammar(
        self, entries: list[dict[str, Any]], label: str, language: str,
    ) -> GrammaticalInfo:
        return GrammaticalInfo()
