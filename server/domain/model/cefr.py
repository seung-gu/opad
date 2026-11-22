"""CEFR (Common European Framework of Reference) level domain rules."""

from typing import Literal, get_args

Level = Literal["A1", "A2", "B1", "B2", "C1", "C2"]


class CEFRLevel:
    """CEFR proficiency level rules for language learning."""

    ALL: list[str] = list(get_args(Level))

    @staticmethod
    def range(max_level: str | None, min_level: str = "A1") -> list[str]:
        """Levels from min_level to max_level, both included.

        range('B2')                  → ['A1', 'A2', 'B1', 'B2']
        range('B2', min_level='A2')  → ['A2', 'B1', 'B2']
        range(None)            → all levels

        A level outside A1-C2 counts as no level and gives all levels,
        because the generate request still takes level as any string (#173).
        """
        if min_level not in CEFRLevel.ALL or max_level not in CEFRLevel.ALL:
            return CEFRLevel.ALL
        return CEFRLevel.ALL[CEFRLevel.ALL.index(min_level) : CEFRLevel.ALL.index(max_level) + 1]

    @staticmethod
    def next(level: str | None) -> str | None:
        """The level one above. C2 stays C2. None or a level outside A1-C2 gives None."""
        if level not in CEFRLevel.ALL:
            return None
        return CEFRLevel.ALL[min(CEFRLevel.ALL.index(level) + 1, len(CEFRLevel.ALL) - 1)]
