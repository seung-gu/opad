"""Domain-level exceptions.

Services raise these errors to express business rule violations.
Route handlers catch them and map to appropriate HTTP status codes.
"""


class DomainError(Exception):
    """Base class for all domain errors."""


class NotFoundError(DomainError):
    """Requested entity does not exist."""


class DuplicateError(DomainError):
    """Entity with the same unique key already exists."""


class PermissionDeniedError(DomainError):
    """Caller lacks permission for the requested action."""


class ValidationError(DomainError):
    """Input violates a business validation rule."""


class DuplicateArticleError(DuplicateError):
    """Duplicate article detected within the dedup window."""

    def __init__(self, article_id: str, job_data: dict | None = None):
        self.article_id = article_id
        self.job_data = job_data
        super().__init__("Duplicate article detected")


class EnqueueError(DomainError):
    """Failed to enqueue a job to the queue."""
