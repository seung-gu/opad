from typing import Protocol
from domain.model.user import User


class UserRepository(Protocol):
    """Protocol defining the interface for user data access."""
    def create(self, email: str, password_hash: str, name: str) -> User | None:
        """Create a new user. Return User or None if creation failed."""
        ...

    def get_by_email(self, email: str) -> User | None:
        """Find a user by email. Return User or None if not found."""
        ...

    def get_by_id(self, user_id: str) -> User | None:
        """Find a user by ID. Return User or None if not found."""
        ...
    
    def update_last_login(self, user_id: str) -> bool:
        """Update the last login timestamp for a user. Return True if successful."""
        ...