"""Streamlit UI for the Plan-It conversational planning agent."""

import requests
import streamlit as st

API_BASE = "http://localhost:8000"

# ── Page config ────────────────────────────────────────────────────
st.set_page_config(page_title="Plan-It", page_icon="📋", layout="wide")


# ── Session initialisation ─────────────────────────────────────────

def init_session():
    """Create a backend session and store the id in Streamlit state."""
    if "session_id" not in st.session_state:
        resp = requests.post(f"{API_BASE}/session")
        resp.raise_for_status()
        st.session_state.session_id = resp.json()["session_id"]
        st.session_state.messages = []  # local chat display list
        st.session_state.current_plan = None
        st.session_state.plan_versions = []
        st.session_state.turn_count = 0
        st.session_state.plan_summary = None
        st.session_state.conversation_summary = None
        st.session_state.last_change_summary = None
        st.session_state.pending_plan = None
        st.session_state.awaiting_confirmation = False


init_session()

# ── Layout ─────────────────────────────────────────────────────────

st.title("📋 Plan-It")
st.caption("Your conversational planning assistant — powered by Gemini")

col_chat, col_plan = st.columns([3, 2])

# ── Plan panel (right) ─────────────────────────────────────────────

with col_plan:
    # ── Pending plan (awaiting confirmation) ────────────────────────
    if st.session_state.awaiting_confirmation and st.session_state.pending_plan:
        st.subheader("📋 Proposed Plan")
        st.warning("⏳ This plan is awaiting your confirmation.")

        pp = st.session_state.pending_plan
        st.markdown(f"### {pp['title']}")
        st.markdown(f"*{pp['overview']}*")

        if st.session_state.plan_summary:
            st.info(f"📝 **Summary:** {st.session_state.plan_summary}")

        st.divider()
        for step in pp.get("steps", []):
            status = step.get("status", "pending")
            icon = {"pending": "⬜", "in-progress": "🔄", "completed": "✅"}.get(status, "⬜")
            with st.expander(f"{icon}  {step['id']}: {step['title']}", expanded=False):
                st.markdown(step["description"])
                st.caption(f"Status: `{status}`")

        st.divider()
        bcol1, bcol2 = st.columns(2)
        with bcol1:
            if st.button("✅ Approve Plan", use_container_width=True, type="primary"):
                st.session_state._auto_msg = "Yes, go ahead and finalize this plan."
                st.rerun()
        with bcol2:
            if st.button("❌ Reject / Revise", use_container_width=True):
                st.session_state._auto_msg = "I'd like to make some changes to this plan."
                st.rerun()

        st.divider()

    # ── Confirmed plan ──────────────────────────────────────────────
    st.subheader("Current Plan")

    if st.session_state.current_plan:
        plan = st.session_state.current_plan
        st.markdown(f"### {plan['title']}")
        st.markdown(f"*{plan['overview']}*")

        # Plan summary
        if st.session_state.plan_summary:
            st.info(f"📝 **Plan Summary:** {st.session_state.plan_summary}")

        # Latest change summary
        if st.session_state.last_change_summary:
            st.success(f"🔀 **Latest Changes:** {st.session_state.last_change_summary}")

        st.divider()

        for step in plan.get("steps", []):
            status = step.get("status", "pending")
            icon = {"pending": "⬜", "in-progress": "🔄", "completed": "✅"}.get(status, "⬜")
            with st.expander(f"{icon}  {step['id']}: {step['title']}", expanded=False):
                st.markdown(step["description"])
                st.caption(f"Status: `{status}`")
    else:
        st.info("No plan yet. Start chatting to create one!")

    # Version history
    if st.session_state.plan_versions:
        st.divider()
        st.subheader("Version History")
        for v in reversed(st.session_state.plan_versions):
            version_num = v.get("version", "?")
            summary = v.get("change_summary", "")
            created = v.get("created_at", "")
            with st.expander(f"v{version_num} — {summary}", expanded=False):
                vp = v.get("plan", {})
                st.markdown(f"**{vp.get('title', '')}**")
                st.markdown(vp.get("overview", ""))
                for s in vp.get("steps", []):
                    st.markdown(f"- [{s.get('status','pending')}] **{s['id']}**: {s['title']}")

    # Conversation summary
    if st.session_state.conversation_summary:
        st.divider()
        st.subheader("Conversation Summary")
        st.markdown(st.session_state.conversation_summary)

    # Session info
    st.divider()
    st.caption(f"Turn count: {st.session_state.turn_count}")
    st.caption(f"Session: `{st.session_state.session_id[:8]}…`")

    if st.button("🔄 New Session", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ── Chat panel (left) ──────────────────────────────────────────────

with col_chat:
    st.subheader("Chat")

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Handle auto-messages from approve/reject buttons
    auto_msg = st.session_state.pop("_auto_msg", None)
    user_input = auto_msg or st.chat_input("Describe your plan or ask a question…")

    # Chat input
    if user_input:
        # Show user message immediately
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Call backend
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                try:
                    resp = requests.post(
                        f"{API_BASE}/chat",
                        json={
                            "session_id": st.session_state.session_id,
                            "message": user_input,
                        },
                        timeout=60,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    assistant_msg = data["response"]
                    st.markdown(assistant_msg)

                    # Update local state
                    st.session_state.messages.append({"role": "assistant", "content": assistant_msg})
                    st.session_state.turn_count = data.get("turn_count", st.session_state.turn_count)

                    if data.get("plan"):
                        if data.get("action") == "PROPOSE":
                            st.session_state.pending_plan = data["plan"]
                            st.session_state.awaiting_confirmation = True
                        elif data.get("action") == "CREATE":
                            st.session_state.current_plan = data["plan"]
                            st.session_state.pending_plan = None
                            st.session_state.awaiting_confirmation = False
                        elif data.get("action") == "UPDATE":
                            st.session_state.current_plan = data["plan"]
                        else:
                            st.session_state.current_plan = data["plan"]

                    st.session_state.awaiting_confirmation = data.get("awaiting_confirmation", False)

                    # Update summaries
                    if data.get("plan_summary"):
                        st.session_state.plan_summary = data["plan_summary"]
                    if data.get("conversation_summary"):
                        st.session_state.conversation_summary = data["conversation_summary"]
                    if data.get("change_summary"):
                        st.session_state.last_change_summary = data["change_summary"]

                    # Refresh plan versions from backend
                    if data.get("plan_version"):
                        ver_resp = requests.get(
                            f"{API_BASE}/session/{st.session_state.session_id}/versions",
                            timeout=10,
                        )
                        if ver_resp.ok:
                            st.session_state.plan_versions = ver_resp.json()

                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to the backend. Make sure the FastAPI server is running on port 8000.")
                except Exception as e:
                    st.error(f"Error: {e}")

        st.rerun()
