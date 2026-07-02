"""Optional Streamlit demo UI over the same LangGraph agent.

The assignment does not require (or score) a UI — the CLI in main.py is the
canonical interface. This is a thin visual layer for live demos: it drives the
exact same compiled graph, including the destructive-delete confirmation gate,
which here renders as Confirm / Cancel buttons instead of a y/n prompt.

Run:  streamlit run streamlit_app.py
"""
import uuid
import streamlit as st
from langgraph.types import Command

from src.graph import DataAgent
from src.observability import flush, observe, update_trace, LANGFUSE_ENABLED
from src import preferences

st.set_page_config(page_title="Retail Data Assistant", page_icon="📊",
                   layout="centered")


@st.cache_resource
def get_agent() -> DataAgent:
    return DataAgent()


agent = get_agent()

# --- session state ---------------------------------------------------------
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "ui-" + uuid.uuid4().hex[:8]
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_report" not in st.session_state:
    st.session_state.last_report = None

thread = {"configurable": {"thread_id": st.session_state.thread_id}}


def pending_interrupt():
    """Return the confirmation payload if the graph is paused, else None."""
    snapshot = agent.graph.get_state(thread)
    for task in snapshot.tasks:
        if task.interrupts:
            return task.interrupts[0].value
    return None


@observe(name="chat_turn", capture_input=False, capture_output=False)
def run_turn(state):
    """One user turn as a single Langfuse trace (mirrors the CLI)."""
    res = agent.graph.invoke(state, config=thread)
    update_trace(user_id=state["user_id"],
                 session_id=st.session_state.thread_id,
                 input=state["user_input"], output=res.get("response", ""))
    return res


@observe(name="chat_turn_resume", capture_input=False, capture_output=False)
def resume_turn(answer, user_id):
    """Resume after a confirmation gate, as its own trace."""
    res = agent.graph.invoke(Command(resume=answer), config=thread)
    update_trace(user_id=user_id, session_id=st.session_state.thread_id,
                 input=f"[confirm: {answer}]", output=res.get("response", ""))
    return res


def record(role: str, content: str):
    st.session_state.messages.append({"role": role, "content": content})


def md(text: str) -> str:
    """Escape '$' so Streamlit doesn't render dollar amounts as LaTeX math."""
    return (text or "").replace("$", "\\$")


# --- sidebar ---------------------------------------------------------------
with st.sidebar:
    st.title("📊 Retail Data Assistant")
    user = st.selectbox("Acting as user", ["manager_a", "manager_b"],
                        help="Scopes saved reports & per-user preferences")
    st.caption(f"Preferred report format: **{preferences.get_format(user)}**")
    st.caption(f"Session: `{st.session_state.thread_id}`")
    st.caption(f"Langfuse tracing: {'ON' if LANGFUSE_ENABLED else 'off'}")
    if st.button("New session"):
        st.session_state.clear()
        st.rerun()
    st.markdown("---")
    st.markdown(
        "**Try:**\n"
        "- Which categories have the highest return rates?\n"
        "- Top 5 markets by revenue\n"
        "- *save that report*\n"
        "- *list my reports*\n"
        "- *open report 1*\n"
        "- *delete all reports about returns*"
    )

# --- history ---------------------------------------------------------------
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(md(m["content"]))

# --- confirmation gate (destructive deletes) -------------------------------
payload = pending_interrupt()
if payload:
    with st.chat_message("assistant"):
        st.warning(payload["prompt"])
        c1, c2 = st.columns(2)
        if c1.button("✅ Confirm delete", use_container_width=True):
            res = resume_turn("yes", user)
            record("assistant", res.get("response", ""))
            flush()
            st.rerun()
        if c2.button("✖ Cancel", use_container_width=True):
            res = resume_turn("no", user)
            record("assistant", res.get("response", ""))
            flush()
            st.rerun()

# --- input -----------------------------------------------------------------
prompt = st.chat_input("Ask about sales, products, customers…",
                       disabled=payload is not None)
if prompt:
    record("user", prompt)
    state = {"user_id": user, "user_input": prompt,
             "last_report": st.session_state.last_report}
    with st.spinner("Analyzing…"):
        res = run_turn(state)
    if res.get("report"):
        st.session_state.last_report = res["report"]
    # If a confirmation gate fired, the response isn't ready yet — the rerun
    # below will render the Confirm/Cancel buttons instead.
    if pending_interrupt() is None:
        record("assistant", res.get("response", ""))
    flush()
    st.rerun()
