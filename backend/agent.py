"""LangGraph-based planning agent with Gemini structured output."""

from __future__ import annotations

import json
import os
from typing import TypedDict, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END
from langgraph.graph.state import StateGraph

from backend.models import (
    ActionType,
    AgentResponse,
    Message,
    MessageRole,
    Plan,
    PlanVersion,
    Session,
)
from backend.context_manager import (
    build_context_messages,
    extract_preferences,
    maybe_compress,
    _format_plan_for_context,
)


# ── Graph state ────────────────────────────────────────────────────

class AgentState(TypedDict):
    session: Session
    user_input: str
    agent_response: Optional[AgentResponse]
    error: Optional[str]


# ── LLM setup ──────────────────────────────────────────────────────

def _get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.7,
    )


# ── System prompt ──────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are **Plan-It**, a conversational planning assistant.

Your job is to help users create, refine, and manage structured plans through natural dialogue.

## Plan creation flow (IMPORTANT — two-step confirmation)
1. **Ask clarifying questions** when the user's request is ambiguous or missing critical details. Don't jump to proposing a plan until you understand the goal.
2. When you have enough information to draft a plan, **propose it** (action = PROPOSE). Include the full plan, a plan_summary, and a change_summary. In `response_to_user`, present the summary and ask the user to confirm: e.g. "Here's what I've put together — shall I go ahead and finalize this plan?"
3. **NEVER use action = CREATE directly** unless the user has explicitly approved a previously proposed plan. When the user confirms (e.g. "yes", "looks good", "go ahead", "approved"), use action = CREATE with the same plan (or the refined version if they requested tweaks).
4. If the user rejects or wants changes to a proposed plan, incorporate their feedback and PROPOSE again.
5. When the user asks to modify an existing *confirmed* plan, use action = UPDATE.
6. When the conversation is casual or informational, use action = NONE.

## General rules
7. Keep `thought` private — use it to reason about what the user wants and what you should do.
8. In `response_to_user`, be friendly, clear, and concise. Reference specific step IDs when discussing plan changes.
9. Assign every step a unique `id` like "step-1", "step-2", etc.
10. When updating a plan, preserve steps that haven't changed and clearly describe what was modified in `change_summary`.
11. Track step statuses: new steps are "pending", mark "in-progress" or "completed" when the user indicates progress.
12. When action is NONE, do NOT populate `plan`, `change_summary`, or `plan_summary`.
13. When action is PROPOSE, CREATE, or UPDATE, you MUST populate `plan`, `change_summary`, and `plan_summary`.

## Summarisation rules
14. **Plan summary (`plan_summary`)**: When proposing, creating, or updating a plan, write a concise 2-4 sentence summary that covers the goal, the number of steps, key milestones, and overall timeline/effort if known.
15. **Change summary (`change_summary`)**: Clearly describe what changed — which steps were added, removed, reordered, or modified, and why.
16. **Conversation summary (`conversation_summary`)**: ALWAYS populate this. Provide a running executive summary of the entire conversation — key decisions made, requirements gathered, constraints identified, current plan state, and any open questions. Keep it under 200 words. Update it every turn.
"""


# ── Node functions ─────────────────────────────────────────────────

async def preprocess_node(state: AgentState) -> AgentState:
    """Add the user message to session, extract preferences, and compress if needed."""
    session = state["session"]
    user_input = state["user_input"]

    # Record the user message
    session.messages.append(Message(role=MessageRole.USER, content=user_input))
    session.turn_count += 1

    # Extract preferences
    session.user_preferences = extract_preferences(user_input, session.user_preferences)

    # Compress if approaching token limit
    llm = _get_llm()
    session = await maybe_compress(session, llm)

    return {**state, "session": session}


async def generate_node(state: AgentState) -> AgentState:
    """Call Gemini to generate the structured agent response."""
    session = state["session"]
    llm = _get_llm()

    # Build messages for the LLM
    context = build_context_messages(session)

    lc_messages = [SystemMessage(content=SYSTEM_PROMPT)]

    # Inject current plan context
    plan_ctx = _format_plan_for_context(session.current_plan)
    if session.current_plan:
        lc_messages.append(SystemMessage(content=f"[Current confirmed plan]\n{plan_ctx}"))

    # Inject pending (proposed) plan if awaiting confirmation
    if session.pending_plan:
        pending_ctx = _format_plan_for_context(session.pending_plan)
        lc_messages.append(SystemMessage(
            content=f"[Pending proposed plan — awaiting user confirmation]\n{pending_ctx}\n"
                    f"The user has NOT yet confirmed this plan. If they approve it, use action=CREATE. "
                    f"If they want changes, PROPOSE a revised version."
        ))

    # Inject user preferences
    if session.user_preferences:
        prefs = json.dumps(session.user_preferences)
        lc_messages.append(SystemMessage(content=f"[Detected user preferences]: {prefs}"))

    # Add conversation history
    for msg in context:
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))
        elif role == "system":
            lc_messages.append(SystemMessage(content=content))

    try:
        # Use structured output so Gemini returns a validated Pydantic object directly
        structured_llm = llm.with_structured_output(AgentResponse)
        agent_resp: AgentResponse = await structured_llm.ainvoke(lc_messages)
        return {**state, "agent_response": agent_resp, "error": None}

    except Exception as e:
        return {**state, "error": str(e)}


async def postprocess_node(state: AgentState) -> AgentState:
    """Update the session with the agent's response — save plan versions, record assistant message."""
    session = state["session"]
    agent_resp = state.get("agent_response")
    error = state.get("error")

    if error or agent_resp is None:
        # Record a fallback assistant message
        fallback = "I'm sorry, I ran into an issue processing your request. Could you try rephrasing?"
        session.messages.append(Message(role=MessageRole.ASSISTANT, content=fallback))
        return {**state, "session": session}

    # Record the assistant reply
    session.messages.append(
        Message(role=MessageRole.ASSISTANT, content=agent_resp.response_to_user)
    )

    # Handle plan propose / create / update
    if agent_resp.action == ActionType.PROPOSE and agent_resp.plan:
        # Store as pending — do NOT finalize yet
        session.pending_plan = agent_resp.plan

    elif agent_resp.action == ActionType.CREATE and agent_resp.plan:
        # User confirmed — promote to current plan
        session.current_plan = agent_resp.plan
        session.pending_plan = None  # clear pending
        version_num = len(session.plan_versions) + 1
        session.plan_versions.append(
            PlanVersion(
                version=version_num,
                plan=agent_resp.plan,
                change_summary=agent_resp.change_summary or "Plan confirmed and created.",
            )
        )

    elif agent_resp.action == ActionType.UPDATE and agent_resp.plan:
        session.current_plan = agent_resp.plan
        version_num = len(session.plan_versions) + 1
        session.plan_versions.append(
            PlanVersion(
                version=version_num,
                plan=agent_resp.plan,
                change_summary=agent_resp.change_summary or "Plan updated.",
            )
        )

    # Persist the rolling conversation summary
    if agent_resp.conversation_summary:
        session.conversation_summary = agent_resp.conversation_summary

    return {**state, "session": session}


# ── Build the graph ────────────────────────────────────────────────

def build_agent_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("preprocess", preprocess_node)
    graph.add_node("generate", generate_node)
    graph.add_node("postprocess", postprocess_node)

    graph.set_entry_point("preprocess")
    graph.add_edge("preprocess", "generate")
    graph.add_edge("generate", "postprocess")
    graph.add_edge("postprocess", END)

    return graph.compile()


# ── Public runner ──────────────────────────────────────────────────

_compiled_graph = None


def _get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_agent_graph()
    return _compiled_graph


async def run_agent(session: Session, user_input: str) -> tuple[Session, AgentResponse | None, str | None]:
    """Run the planning agent for one turn.

    Returns (updated_session, agent_response_or_None, error_or_None).
    """
    graph = _get_graph()

    initial_state: AgentState = {
        "session": session,
        "user_input": user_input,
        "agent_response": None,
        "error": None,
    }

    result = await graph.ainvoke(initial_state)

    return result["session"], result.get("agent_response"), result.get("error")
