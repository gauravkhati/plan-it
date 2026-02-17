"""Context manager – handles conversation history, compression, and preference tracking."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from backend.models import Message, MessageRole, Plan, Session

# Simulated token limit (8 000 tokens).  We approximate 1 token ≈ 4 chars.
TOKEN_LIMIT = 8_000
CHARS_PER_TOKEN = 4
CHAR_LIMIT = TOKEN_LIMIT * CHARS_PER_TOKEN  # close to 32 000 chars

# When we hit 75 % of the limit we compress.
COMPRESSION_THRESHOLD = int(CHAR_LIMIT * 0.75)


def _estimate_tokens(text: str) -> int:
    """Rough token estimate."""
    return len(text) // CHARS_PER_TOKEN


def _estimate_message_tokens(messages: list[Message]) -> int:
    return sum(_estimate_tokens(m.content) for m in messages)


def _format_plan_for_context(plan: Optional[Plan]) -> str:
    if plan is None:
        return "No plan has been created yet."
    lines = [f"## Current Plan: {plan.title}", f"**Overview:** {plan.overview}", "### Steps:"]
    for step in plan.steps:
        lines.append(f"- [{step.status.value}] **{step.id}: {step.title}** – {step.description}")
    return "\n".join(lines)


# ── Preference extraction ──────────────────────────────────────────

_PREFERENCE_KEYWORDS = {
    "detail_level": {
        "detailed": "detailed",
        "brief": "brief",
        "concise": "brief",
        "verbose": "detailed",
        "short": "brief",
    },
    "tone": {
        "formal": "formal",
        "casual": "casual",
        "professional": "formal",
        "friendly": "casual",
    },
}


def extract_preferences(text: str, existing: dict) -> dict:
    """Very lightweight keyword-based preference extraction."""
    lower = text.lower()
    updated = dict(existing)
    for pref_key, keywords in _PREFERENCE_KEYWORDS.items():
        for word, value in keywords.items():
            if word in lower:
                updated[pref_key] = value
    return updated



async def compress_history(
    messages: list[Message],
    current_plan: Optional[Plan],
    user_preferences: dict,
    llm: ChatGoogleGenerativeAI,
) -> str:
    """Compress the conversation history into a concise summary using the LLM."""

    history_text = "\n".join(
        f"[{m.role.value}] {m.content}" for m in messages
    )
    plan_text = _format_plan_for_context(current_plan)
    prefs_text = json.dumps(user_preferences) if user_preferences else "None detected."

    compression_prompt = f"""You are a context-compression assistant.
Summarize the following conversation into a concise paragraph that preserves:
1. The user's original goal and all key requirements.
2. Every decision, preference, and constraint mentioned.
3. The current state of the plan (included below for reference).
4. Any open questions or pending items.

Keep the summary under 600 words.

--- CONVERSATION ---
{history_text}

--- CURRENT PLAN ---
{plan_text}

--- DETECTED USER PREFERENCES ---
{prefs_text}
"""

    response = await llm.ainvoke([
        SystemMessage(content="You summarize conversations accurately and concisely."),
        HumanMessage(content=compression_prompt),
    ])
    return response.content


def build_context_messages(session: Session) -> list[dict]:
    """Build the message list to send to the LLM, respecting the token budget.

    Returns a list of dicts with 'role' and 'content' keys suitable for
    LangChain message constructors.
    """
    context_parts: list[dict] = []

    # If we have a compressed context, inject it as a system note first.
    if session.compressed_context:
        context_parts.append({
            "role": "system",
            "content": f"[Compressed prior context]\n{session.compressed_context}",
        })

    # Append remaining messages (newest portion kept after compression).
    for msg in session.messages:
        if msg.is_blocked:
            continue
        context_parts.append({"role": msg.role.value, "content": msg.content})

    return context_parts


async def maybe_compress(session: Session, llm: ChatGoogleGenerativeAI) -> Session:
    """Check if the session's history exceeds the threshold and compress if needed.

    Returns a *new* Session object (does not mutate in-place).
    """
    total_chars = sum(len(m.content) for m in session.messages)
    if session.compressed_context:
        total_chars += len(session.compressed_context)

    if total_chars < COMPRESSION_THRESHOLD:
        return session

    # Compress everything except the last 4 messages (keep recent context).
    keep_recent = 4
    messages_to_compress = session.messages[:-keep_recent] if len(session.messages) > keep_recent else []
    recent_messages = session.messages[-keep_recent:] if len(session.messages) > keep_recent else session.messages

    if not messages_to_compress and not session.compressed_context:
        return session  # Nothing useful to compress

    # Combine old compressed context + messages to compress
    all_to_compress = []
    if session.compressed_context:
        all_to_compress.append(
            Message(role=MessageRole.SYSTEM, content=f"[Prior compressed context]: {session.compressed_context}")
        )
    all_to_compress.extend(messages_to_compress)

    compressed = await compress_history(all_to_compress, session.current_plan, session.user_preferences, llm)

    new_session = deepcopy(session)
    new_session.compressed_context = compressed
    new_session.messages = list(recent_messages)
    return new_session
