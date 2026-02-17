"""Utility for parsing JSON from LLM response content."""

import json
import logging

logger = logging.getLogger(__name__)


def parse_json_from_content(content: str) -> dict | None:
    """Parse JSON from LLM response content.

    Handles various formats:
    - Plain JSON: {"key": "value"}
    - JSON in markdown code blocks: ```json {...} ```
    - JSON with surrounding text

    Args:
        content: Raw content string from LLM

    Returns:
        Parsed JSON dict, or None if parsing fails
    """
    try:
        if "```json" in content:
            json_match = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            json_match = content.split("```")[1].split("```")[0]
        elif "{" in content:
            start = content.index("{")
            end = content.rindex("}") + 1
            json_match = content[start:end]
        else:
            json_match = content

        return json.loads(json_match.strip())
    except (ValueError, IndexError) as e:
        logger.debug("Failed to parse JSON from content", extra={
            "error": str(e),
            "content_preview": content[:200]
        })
        return None
