"""In-memory implementation of UserRepository for testing."""

import uuid
from datetime import datetime, timezone
from domain.model.user import User


class FakeUserRepository:
    def __init__(self):
        self.store: dict[str, User] = {}

    # ── write operations ─────────────────────────────────────

    def create(self, email: str, password_hash: str, name: str) -> User | None:
        if any(u.email == email for u in self.store.values()):
            return None

        user_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)

        user = User(
            id=user_id,
            name=name,
            email=email,
            created_at=now,
            updated_at=now,
            password_hash=password_hash,
            provider='email',
        )
        self.store[user_id] = user
        return user

    def update_last_login(self, user_id: str) -> bool:
        user = self.store.get(user_id)
        if not user:
            return False

        now = datetime.now(timezone.utc)
        user.last_login = now
        user.updated_at = now
        return True

    # ── read operations ──────────────────────────────────────

    def get_by_email(self, email: str) -> User | None:
        for user in self.store.values():
            if user.email == email:
                return user
        return None

    def get_by_id(self, user_id: str) -> User | None:
        return self.store.get(user_id)
