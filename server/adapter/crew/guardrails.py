"""Custom guardrails for CrewAI task validation.

Provides JSON repair functionality to handle malformed LLM outputs.
"""

import json
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


def require_articles(result: TaskOutput) -> tuple[bool, Any]:
    """Repair JSON, then reject an empty article list.

    A dead search tool (expired SERPER_API_KEY, exhausted quota) yields a
    well-formed but empty list. Without this check the crew carries on, the
    next task correctly reports it has nothing to pick, and the run dies two
    steps later on a Pydantic error that names neither the search nor the key.
    Failing here keeps the error next to its cause.
    """
    ok, output = repair_json_output(result)
    if not ok:
        return (ok, output)

    try:
        data = json.loads(output)
    except json.JSONDecodeError as e:
        return (False, f"Output is not valid JSON after repair: {e}")

    articles = data.get('articles') if isinstance(data, dict) else None
    if not articles:
        logger.error(
            "No news articles found — the search tool returned nothing. "
            "Check SERPER_API_KEY validity and remaining quota."
        )
        return (False, "No news articles were found. The search returned no results.")

    return (True, output)


def require_selected_article(result: TaskOutput) -> tuple[bool, Any]:
    """Repair JSON, then reject a selection that picked nothing.

    The picker prompt tells the agent to return null when no candidate is even
    remotely related to the topic (tasks.yaml), but SelectedArticle.article is
    a required NewsArticle. So the documented answer for "nothing fits" killed
    the run on a Pydantic error about article being None — an error that named
    neither the topic nor the picker.

    Guardrails run before output_pydantic conversion, so rejecting it here
    gives the agent a message it can retry against, and leaves a last failure
    a reader can understand.
    """
    ok, output = repair_json_output(result)
    if not ok:
        return (ok, output)

    try:
        data = json.loads(output)
    except json.JSONDecodeError as e:
        return (False, f"Output is not valid JSON after repair: {e}")

    article = data.get('article') if isinstance(data, dict) else None
    if not isinstance(article, dict) or not article:
        logger.error(
            "No article was selected — the picker found nothing matching the topic "
            "among the candidates the search returned."
        )
        return (
            False,
            "No article was selected. Choose the closest candidate from the provided "
            "list; the rewriter will adjust length and level.",
        )

    return (True, output)
