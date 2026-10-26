"""DeskPilot - Streamlit UI.   Run:  streamlit run app.py"""
import pandas as pd
import streamlit as st

from agents.orchestrator import Orchestrator
from common import config, db

st.set_page_config(page_title="DeskPilot IT Help Desk", page_icon=":material/support_agent:", layout="wide")


@st.cache_resource(show_spinner="Connecting to Foundry...")
def get_orchestrator() -> Orchestrator:
    config.require("PROJECT_ENDPOINT", "AZURE_OPENAI_ENDPOINT")
    return Orchestrator()


def reset_chat(user: str) -> None:
    st.session_state.session = get_orchestrator().new_session(user)
    st.session_state.messages = []


# --- Sidebar: sign-in simulation + the signed-in user's tickets ------------------
with st.sidebar:
    st.title("DeskPilot")
    user = st.selectbox("Signed in as", list(config.USERS), format_func=lambda u: f"{config.USERS[u]['name']} ({config.USERS[u]['role']})")
    if st.session_state.get("user") != user:  # switching user starts a new conversation
        st.session_state.user = user
        reset_chat(user)
    if st.button("New conversation"):
        reset_chat(user)
    st.subheader("Tickets")
    tickets_box = st.empty()


def show_tickets() -> None:
    rows = db.list_tickets(user, limit=200)
    frame = pd.DataFrame(rows, columns=["id", "title", "priority", "status"]) if rows else pd.DataFrame()
    tickets_box.dataframe(frame, hide_index=True, width="stretch")


def render_trace(reply) -> None:
    """Show how the answer was produced: route, tools, citations."""
    # TODO 3.2.b: Inside st.expander("How this answer was produced"): show reply.route,
    # reply.agent and reply.reason; list each tool in reply.tools; list each citation in
    # reply.citations (title and url)
    with st.expander("How this answer was produced"):
        st.write(f"**Route:** {reply.route} -> **{reply.agent}** agent. {reply.reason}")
        for tool in reply.tools:
            st.write(f"- Tool: `{tool['name']}` ({tool['type']})")
        for citation in reply.citations:
            label = citation.get("title") or citation.get("url") or "source"
            st.write(f"- Source: [{label}]({citation['url']})" if citation.get("url") else f"- Source: {label}")


st.title("DeskPilot IT Help Desk")
st.caption("Ask an IT question, or ask me to create, check or update a ticket.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["text"])
        for path in message.get("files", []):
            st.image(path)
        if message.get("reply"):
            render_trace(message["reply"])

prompt = st.chat_input("How can I help?")
if prompt:
    st.session_state.messages.append({"role": "user", "text": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Working..."):
            # TODO 3.2.a: Call get_orchestrator().handle(st.session_state.session, prompt) and
            # keep the result in a variable named reply
            reply = get_orchestrator().handle(st.session_state.session, prompt)
        if reply.blocked:
            st.warning(reply.text)
        elif reply.error:
            st.error(reply.text)
            st.caption(reply.error)
        else:
            st.markdown(reply.text)
        for path in reply.files:
            st.image(path)
        render_trace(reply)
    st.session_state.messages.append({"role": "assistant", "text": reply.text, "files": reply.files, "reply": reply})

show_tickets()
