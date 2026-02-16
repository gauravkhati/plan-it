"""Session store abstraction with optional MongoDB persistence.

If MONGODB_URI is set in the environment, sessions are persisted to MongoDB.
Otherwise, falls back to an in-memory dictionary (stateless across restarts).
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

from backend.models import Session

logger = logging.getLogger(__name__)


# ── Abstract interface ─────────────────────────────────────────────

class SessionStore(ABC):
    """Base class for session storage backends."""

    @abstractmethod
    async def get(self, session_id: str) -> Optional[Session]:
        ...

    @abstractmethod
    async def save(self, session: Session) -> None:
        ...

    @abstractmethod
    async def delete(self, session_id: str) -> None:
        ...

    @abstractmethod
    async def exists(self, session_id: str) -> bool:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[dict]:
        """Return lightweight session summaries for a user."""
        ...


# ── In-memory store ────────────────────────────────────────────────

class InMemorySessionStore(SessionStore):
    """Simple dict-backed store. Data is lost on restart."""

    def __init__(self) -> None:
        self._store: dict[str, Session] = {}

    async def get(self, session_id: str) -> Optional[Session]:
        return self._store.get(session_id)

    async def save(self, session: Session) -> None:
        self._store[session.session_id] = session

    async def delete(self, session_id: str) -> None:
        self._store.pop(session_id, None)

    async def exists(self, session_id: str) -> bool:
        return session_id in self._store

    async def list_by_user(self, user_id: str) -> list[dict]:
        results = []
        for s in self._store.values():
            if s.user_id == user_id:
                results.append({
                    "session_id": s.session_id,
                    "plan_name": s.plan_name or (s.current_plan.title if s.current_plan else None),
                    "turn_count": s.turn_count,
                    "has_plan": s.current_plan is not None,
                })
        return results


# ── MongoDB store ──────────────────────────────────────────────────

class MongoSessionStore(SessionStore):
    """Async MongoDB-backed store using Motor."""

    def __init__(self, uri: str, db_name: str = "plan_it", collection_name: str = "sessions") -> None:
        from motor.motor_asyncio import AsyncIOMotorClient  # deferred import

        self._client = AsyncIOMotorClient(uri)
        self._db = self._client[db_name]
        self._collection = self._db[collection_name]
        logger.info("MongoDB session store connected → %s.%s", db_name, collection_name)

    async def get(self, session_id: str) -> Optional[Session]:
        doc = await self._collection.find_one({"session_id": session_id})
        if doc is None:
            return None
        doc.pop("_id", None)  # remove Mongo internal field
        return Session.model_validate(doc)

    async def save(self, session: Session) -> None:
        data = session.model_dump(mode="json")
        await self._collection.replace_one(
            {"session_id": session.session_id},
            data,
            upsert=True,
        )

    async def delete(self, session_id: str) -> None:
        await self._collection.delete_one({"session_id": session_id})

    async def exists(self, session_id: str) -> bool:
        count = await self._collection.count_documents({"session_id": session_id}, limit=1)
        return count > 0

    async def list_by_user(self, user_id: str) -> list[dict]:
        cursor = self._collection.find(
            {"user_id": user_id},
            {"session_id": 1, "plan_name": 1, "turn_count": 1, "current_plan.title": 1, "_id": 0},
        )
        results = []
        async for doc in cursor:
            results.append({
                "session_id": doc["session_id"],
                "plan_name": doc.get("plan_name") or (doc.get("current_plan", {}) or {}).get("title"),
                "turn_count": doc.get("turn_count", 0),
                "has_plan": doc.get("current_plan") is not None,
            })
        return results

    async def close(self) -> None:
        self._client.close()


# ── Factory ────────────────────────────────────────────────────────

def create_session_store() -> SessionStore:
    """Create the appropriate store based on environment config.

    Set MONGODB_URI in .env to enable MongoDB persistence.
    Optionally set MONGODB_DB_NAME (default: "plan_it").
    """
    mongo_uri = os.getenv("MONGODB_URI")
    if mongo_uri:
        db_name = os.getenv("MONGODB_DB_NAME", "plan_it")
        logger.info("Using MongoDB session store (db=%s)", db_name)
        return MongoSessionStore(uri=mongo_uri, db_name=db_name)
    else:
        logger.info("MONGODB_URI not set — using in-memory session store (sessions won't survive restarts)")
        return InMemorySessionStore()
