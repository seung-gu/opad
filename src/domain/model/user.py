from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    """Domain model representing a user."""
    id: str
    name: str
    email: str
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None = None
    password_hash: str | None = None
    provider: str = 'email'
