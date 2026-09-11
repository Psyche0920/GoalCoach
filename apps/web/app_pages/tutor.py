"""Tutor — chat with the GoalCoach tutoring agent via the backend API."""

from __future__ import annotations

import streamlit as st

from goalcoach_api import send_chat

STARTERS = [
    "What should I study today?",
    "Quiz me on HSK 1 greetings",
    "Explain the difference between 了 and 过",
    "Give me a practice sentence for 学习",
]

learner_id = st.session_state.get("learner_id")

if "messages" not in st.session_state:
    st.session_state.messages = []

st.caption(f"Chatting as learner `{learner_id}` — replies come from the GoalCoach tutor API.")


def render_message(message: dict) -> None:
    role = message.get("role", "assistant")
    avatar = ":material/school:" if role == "assistant" else ":material/person:"
    with st.chat_message(role, avatar=avatar):
        st.markdown(message.get("content") or "")
        grammar_points = message.get("grammar_points") or []
        if grammar_points:
            chips = " ".join(
                f":blue-badge[{point}]" for point in grammar_points[:6]
            )
            st.markdown("Grammar points: " + chips)
        suggested = message.get("suggested_practice")
        if suggested:
            st.caption(f":material/touch_app: Try next: {suggested}")
        provider = message.get("provider")
        if provider:
            st.markdown(
                f"<div style='text-align:right;opacity:.55;font-size:.8rem'>{provider}</div>",
                unsafe_allow_html=True,
            )


def run_chat(prompt: str) -> None:
    st.session_state.messages.append({"role": "user", "content": prompt})
    payload, error = send_chat(learner_id, prompt)
    if error:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": f"⚠️ Could not reach the tutor: {error}",
            }
        )
    else:
        response = payload.get("response", {})
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response.get("reply") or "",
                "grammar_points": response.get("grammar_points") or [],
                "suggested_practice": response.get("suggested_practice"),
                "provider": payload.get("provider"),
            }
        )
    st.rerun()


if st.session_state.get("messages"):
    if st.button("Clear conversation", icon=":material/delete:", help="Start fresh"):
        st.session_state.messages = []
        st.rerun()

for message in st.session_state.get("messages", []):
    render_message(message)

if not st.session_state.get("messages"):
    st.caption("Quick start ideas")
    starter_cols = st.columns(len(STARTERS))
    for index, starter in enumerate(STARTERS):
        if starter_cols[index].button(starter, width="stretch"):
            run_chat(starter)

if prompt := st.chat_input("Talk to your tutor…", accept_file=False):
    run_chat(prompt)