"""Authentication utilities — password hashing, JWT tokens, user model."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from pydantic import BaseModel, Field
import bcrypt
import jwt

logger = logging.getLogger(__name__)

# ── Password hashing ─────
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))


# ── JWT helpers ─────
SECRET_KEY = os.getenv("JWT_SECRET", "plan-it-dev-secret-change-me")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 72


def create_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Return payload dict or None if invalid / expired."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


# ── User model ───────
class User(BaseModel):
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    hashed_password: str
    display_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── User store abstraction ────

class UserStore:
    """Simple in-memory user store. Can be replaced with Mongo later."""

    def __init__(self) -> None:
        self._users: dict[str, User] = {}      
        self._emails: dict[str, str] = {}       

    async def get_by_id(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        uid = self._emails.get(email.lower())
        return self._users.get(uid) if uid else None

    async def create(self, user: User) -> None:
        self._users[user.user_id] = user
        self._emails[user.email.lower()] = user.user_id

    async def exists_email(self, email: str) -> bool:
        return email.lower() in self._emails


class MongoUserStore(UserStore):
    """MongoDB-backed user store."""

    def __init__(self, db) -> None:
        self._collection = db["users"]

    async def get_by_id(self, user_id: str) -> Optional[User]:
        doc = await self._collection.find_one({"user_id": user_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return User.model_validate(doc)

    async def get_by_email(self, email: str) -> Optional[User]:
        doc = await self._collection.find_one({"email": email.lower()})
        if doc is None:
            return None
        doc.pop("_id", None)
        return User.model_validate(doc)

    async def create(self, user: User) -> None:
        data = user.model_dump(mode="json")
        data["email"] = data["email"].lower()
        await self._collection.insert_one(data)
        # Ensure unique email index
        await self._collection.create_index("email", unique=True)

    async def exists_email(self, email: str) -> bool:
        count = await self._collection.count_documents({"email": email.lower()}, limit=1)
        return count > 0


# ── Request / Response schemas ──────

class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: str
    email: str
    display_name: Optional[str] = None
