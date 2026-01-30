"""Token usage tracking for article generation using LiteLLM callbacks.

This module provides a custom LiteLLM callback handler that tracks token usage
during CrewAI article generation and saves usage records to MongoDB.

The tracker is integrated with the worker's process_job() function and uses
LiteLLM's callback system to intercept all LLM API calls made during article
generation.

Architecture:
    process_job() -> set litellm.callbacks -> run_crew() -> LLM calls
                                                          -> ArticleGenerationTokenTracker
                                                          -> save_token_usage()
"""

import logging
from typing import Any

import litellm
from litellm.integrations.custom_logger import CustomLogger

from utils.mongodb import save_token_usage

logger = logging.getLogger(__name__)


class ArticleGenerationTokenTracker(CustomLogger):
    """LiteLLM callback handler for tracking token usage during article generation.

    This callback handler intercepts all LLM API calls made through LiteLLM
    (including those made by CrewAI) and records token usage to MongoDB.

    Attributes:
        job_id: The job ID for the current article generation.
        user_id: The user ID who initiated the generation.
        article_id: The article ID being generated.

    Usage:
        tracker = ArticleGenerationTokenTracker(
            job_id="job-123",
            user_id="user-456",
            article_id="article-789"
        )
        litellm.callbacks = [tracker]
        # ... run CrewAI ...
        litellm.callbacks = []  # cleanup
    """

    def __init__(
        self,
        job_id: str,
        user_id: str,
        article_id: str | None = None
    ) -> None:
        """Initialize the token tracker.

        Args:
            job_id: Job ID for the current article generation.
            user_id: User ID who initiated the generation.
            article_id: Optional article ID being generated.
        """
        super().__init__()
        self.job_id = job_id
        self.user_id = user_id
        self.article_id = article_id

    def log_success_event(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: float,
        end_time: float
    ) -> None:
        """Handle successful LLM API call completion.

        Called by LiteLLM after each successful LLM API call. Extracts token
        usage information from the response and saves it to MongoDB.

        Args:
            kwargs: Original kwargs passed to the LLM call.
            response_obj: The response object from the LLM provider.
            start_time: Unix timestamp when the call started.
            end_time: Unix timestamp when the call completed.
        """
        try:
            # Extract model name from kwargs or response
            model = kwargs.get("model", "unknown")
            if hasattr(response_obj, "model") and response_obj.model:
                model = response_obj.model

            # Extract token usage from response
            prompt_tokens = 0
            completion_tokens = 0

            if hasattr(response_obj, "usage") and response_obj.usage:
                usage = response_obj.usage
                prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
                completion_tokens = getattr(usage, "completion_tokens", 0) or 0

            # Skip if no tokens were used (shouldn't happen but be safe)
            if prompt_tokens == 0 and completion_tokens == 0:
                logger.debug(
                    "Skipping token tracking - no tokens used",
                    extra={"jobId": self.job_id, "model": model}
                )
                return

            # Calculate cost using LiteLLM's built-in pricing
            estimated_cost = 0.0
            try:
                estimated_cost = litellm.completion_cost(completion_response=response_obj)
            except Exception as cost_err:
                logger.debug(
                    "Could not calculate cost with LiteLLM",
                    extra={
                        "jobId": self.job_id,
                        "model": model,
                        "error": str(cost_err)
                    }
                )

            # Save token usage to MongoDB
            metadata = {"job_id": self.job_id}

            save_token_usage(
                user_id=self.user_id,
                operation="article_generation",
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                estimated_cost=estimated_cost,
                article_id=self.article_id,
                metadata=metadata
            )

            logger.debug(
                "Token usage tracked for article generation",
                extra={
                    "jobId": self.job_id,
                    "articleId": self.article_id,
                    "model": model,
                    "promptTokens": prompt_tokens,
                    "completionTokens": completion_tokens,
                    "estimatedCost": estimated_cost
                }
            )

        except Exception as e:
            # Never let tracking failures crash the worker
            logger.warning(
                "Failed to track token usage (non-fatal)",
                extra={
                    "jobId": self.job_id,
                    "error": str(e),
                    "errorType": type(e).__name__
                }
            )

    async def async_log_success_event(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: float,
        end_time: float
    ) -> None:
        """Async version of log_success_event.

        Delegates to the synchronous version since MongoDB operations are
        synchronous in this codebase.

        Args:
            kwargs: Original kwargs passed to the LLM call.
            response_obj: The response object from the LLM provider.
            start_time: Unix timestamp when the call started.
            end_time: Unix timestamp when the call completed.
        """
        self.log_success_event(kwargs, response_obj, start_time, end_time)

    def log_failure_event(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: float,
        end_time: float
    ) -> None:
        """Handle failed LLM API call.

        Called by LiteLLM when an LLM API call fails. Only logs the failure
        for observability; does not save to MongoDB since no tokens were
        consumed successfully.

        Args:
            kwargs: Original kwargs passed to the LLM call.
            response_obj: The error/response object from the LLM provider.
            start_time: Unix timestamp when the call started.
            end_time: Unix timestamp when the call completed/failed.
        """
        try:
            model = kwargs.get("model", "unknown")
            error_msg = str(response_obj) if response_obj else "Unknown error"

            logger.debug(
                "LLM call failed during article generation",
                extra={
                    "jobId": self.job_id,
                    "articleId": self.article_id,
                    "model": model,
                    "error": error_msg[:200]  # Truncate long error messages
                }
            )
        except Exception as e:
            # Never let logging failures crash the worker
            logger.warning(
                "Failed to log LLM failure event (non-fatal)",
                extra={"jobId": self.job_id, "error": str(e)}
            )

    async def async_log_failure_event(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: float,
        end_time: float
    ) -> None:
        """Async version of log_failure_event.

        Delegates to the synchronous version.

        Args:
            kwargs: Original kwargs passed to the LLM call.
            response_obj: The error/response object from the LLM provider.
            start_time: Unix timestamp when the call started.
            end_time: Unix timestamp when the call completed/failed.
        """
        self.log_failure_event(kwargs, response_obj, start_time, end_time)
