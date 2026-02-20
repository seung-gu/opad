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
