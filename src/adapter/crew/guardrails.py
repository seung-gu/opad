"""Custom guardrails for CrewAI task validation.

Provides JSON repair functionality to handle malformed LLM outputs.
"""

import logging
from typing import Any

from crewai import TaskOutput
from json_repair import repair_json

logger = logging.getLogger(__name__)


def repair_json_output(result: TaskOutput) -> tuple[bool, Any]:
    """Repair malformed JSON in task output before Pydantic validation.

    LLMs sometimes produce invalid JSON (missing commas, unclosed brackets,
    unescaped characters). This guardrail attempts to repair such errors
    using the json-repair library.

    Args:
        result: TaskOutput from CrewAI task

    Returns:
        Tuple of (success, repaired_output or error_message)
    """
    try:
        raw_output = result.raw

        # Skip if output is empty
        if not raw_output or not raw_output.strip():
            return (False, "Empty output received")

        # Attempt to repair the JSON
        # Note: Non-Latin chars (Korean, etc.) may be Unicode-escaped but remain valid JSON
        repaired = repair_json(raw_output)

        # Log if repair was needed
        if repaired != raw_output:
            logger.info(
                "JSON repaired successfully",
                extra={"original_length": len(raw_output), "repaired_length": len(repaired)}
            )

        return (True, repaired)

    except Exception as e:
        logger.warning(
            f"JSON repair failed: {e}",
            extra={"error": str(e), "errorType": type(e).__name__}
        )
        return (False, f"JSON repair failed: {str(e)}")
