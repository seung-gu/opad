"""CEFR (Common European Framework of Reference) level domain rules."""


class CEFRLevel:
    """CEFR proficiency level rules for language learning."""

    ALL = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']

    @staticmethod
    def range(target: str | None, max_above: int = 1) -> list[str]:
        """Get CEFR levels up to target + max_above.

        Includes all levels from A1 up to (target + max_above).

        Args:
            target: Center CEFR level (A1-C2). None/empty returns all.
            max_above: Levels above target to include (default: 1).

        Examples:
            CEFRLevel.range('B1')         → ['A1', 'A2', 'B1', 'B2']
            CEFRLevel.range('B1', 0)      → ['A1', 'A2', 'B1']
            CEFRLevel.range(None)          → ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
        """
        if not target or not target.strip():
            return CEFRLevel.ALL
        target_upper = target.upper()
        if target_upper not in CEFRLevel.ALL:
            return CEFRLevel.ALL

        idx = CEFRLevel.ALL.index(target_upper)
        hi = min(idx + max_above, len(CEFRLevel.ALL) - 1)
        return CEFRLevel.ALL[:hi + 1]
