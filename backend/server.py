"""FastAPI server for the Plan-It conversational planning agent."""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.models import (
    ActionType,
    ChatRequest,
    ChatResponse,
    Plan,
    Session,
)
from backend.agent import run_agent
from backend.session_store import SessionStore, MongoSessionStore, create_session_store
from backend.auth import (
    User,
    UserStore,
    MongoUserStore,
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    hash_password,
    verify_password,
    create_token,
    decode_token,
)

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Session store
store: SessionStore | None = None
user_store: UserStore | None = None
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    global store, user_store
    store = create_session_store()
    if isinstance(store, MongoSessionStore):
        user_store = MongoUserStore(store._db)
    else:
        user_store = UserStore()
    logger.info("Session store ready: %s", type(store).__name__)
    yield
    #cleanup
    if isinstance(store, MongoSessionStore):
        await store.close()
        logger.info("MongoDB connection closed.")


app = FastAPI(title="Plan-It API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# auth endpoints
async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Validate JWT and return User object."""
    payload = decode_token(creds.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    user = await user_store.get_by_id(payload["sub"])
    if user is None:
        raise HTTPException(status_code=401, detail="User not found.")
    return user




@app.post("/auth/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
    """Register a new user."""
    if await user_store.exists_email(req.email):
        raise HTTPException(status_code=409, detail="Email already registered.")
    user = User(
        email=req.email.lower(),
        hashed_password=hash_password(req.password),
        display_name=req.display_name,
    )
    await user_store.create(user)
    token = create_token(user.user_id, user.email)
    return AuthResponse(token=token, user_id=user.user_id, email=user.email, display_name=user.display_name)


@app.post("/auth/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    """Authenticate and return a JWT."""
    user = await user_store.get_by_email(req.email)
    if user is None or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = create_token(user.user_id, user.email)
    return AuthResponse(token=token, user_id=user.user_id, email=user.email, display_name=user.display_name)


@app.get("/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    """Return current user info."""
    return {"user_id": user.user_id, "email": user.email, "display_name": user.display_name}




@app.post("/session", response_model=dict)
async def create_session(user: User = Depends(get_current_user)):
    """Create a new conversation session for the authenticated user."""
    session_id = str(uuid.uuid4())
    session = Session(session_id=session_id, user_id=user.user_id)
    await store.save(session)
    return {"session_id": session_id}


@app.get("/sessions", response_model=list)
async def list_sessions(user: User = Depends(get_current_user)):
    """List all sessions for the authenticated user."""
    return await store.list_by_user(user.user_id)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, user: User = Depends(get_current_user)):
    """Send a message and get the agent's response."""
    session = await store.get(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found. Create one first via POST /session.")
    if session.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    updated_session, agent_resp, error = await run_agent(session, req.message)

    # Persist updated session
    await store.save(updated_session)

    if error or agent_resp is None:
        return ChatResponse(
            response="Sorry, something went wrong. Please try again.",
            plan=updated_session.current_plan,
            action=ActionType.NONE,
            change_summary=None,
            plan_summary=None,
            conversation_summary=updated_session.conversation_summary,
            turn_count=updated_session.turn_count,
            plan_version=len(updated_session.plan_versions) if updated_session.plan_versions else None,
        )

    return ChatResponse(
        response=agent_resp.response_to_user,
        plan=agent_resp.plan if agent_resp.action != ActionType.NONE else updated_session.current_plan,
        action=agent_resp.action,
        change_summary=agent_resp.change_summary,
        plan_summary=agent_resp.plan_summary,
        conversation_summary=agent_resp.conversation_summary,
        turn_count=updated_session.turn_count,
        plan_version=len(updated_session.plan_versions) if updated_session.plan_versions else None,
        awaiting_confirmation=updated_session.pending_plan is not None,
    )


@app.get("/session/{session_id}", response_model=dict)
async def get_session(session_id: str, user: User = Depends(get_current_user)):
    """Retrieve session metadata (plan, turn count, versions)."""
    session = await store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return {
        "session_id": session.session_id,
        "turn_count": session.turn_count,
        "current_plan": session.current_plan.model_dump() if session.current_plan else None,
        "plan_versions": [v.model_dump() for v in session.plan_versions],
        "user_preferences": session.user_preferences,
        "conversation_summary": session.conversation_summary,
        "has_compressed_context": session.compressed_context is not None,
    }


@app.get("/session/{session_id}/history", response_model=list)
async def get_history(session_id: str, user: User = Depends(get_current_user)):
    """Return the conversation history for a session."""
    session = await store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return [{"role": m.role.value, "content": m.content, "timestamp": m.timestamp.isoformat()} for m in session.messages]


@app.get("/session/{session_id}/versions", response_model=list)
async def get_plan_versions(session_id: str, user: User = Depends(get_current_user)):
    """Return all plan versions for a session."""
    session = await store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return [v.model_dump() for v in session.plan_versions]


@app.get("/health")
async def health():
    """Health check — also reports which storage backend is active."""
    return {
        "status": "ok",
        "store": type(store).__name__ if store else "not initialised",
    }


@app.get("/session/{session_id}/summary", response_model=dict)
async def get_conversation_summary(session_id: str, user: User = Depends(get_current_user)):
    """Return the latest executive conversation summary."""
    session = await store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return {
        "session_id": session.session_id,
        "turn_count": session.turn_count,
        "conversation_summary": session.conversation_summary,
        "has_plan": session.current_plan is not None,
        "plan_version": len(session.plan_versions) if session.plan_versions else 0,
    }
