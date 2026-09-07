"""
apps/web/app.py
Streamlit prototype chat UI for testing GoalCoach PydanticAI tutoring endpoint.
"""

from __future__ import annotations

import httpx
import streamlit as st

API_URL = "http://localhost:8000/api/v1"

st.set_page_config(page_title="GoalCoach — HSK Tutor", page_icon="🇨🇳", layout="wide")
st.title("GoalCoach: Adaptive Chinese Tutor (PydanticAI)")

if "learner_id" not in st.session_state:
    st.session_state.learner_id = "00000000-0000-0000-0000-000000000001"
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar info
st.sidebar.header("Learner Profile")
st.sidebar.text(f"ID: {st.session_state.learner_id}")
st.sidebar.caption("Orchestrator: Deterministic State Machine")
st.sidebar.caption("Agents: PydanticAI (OpenRouter + Ollama Gemma 4)")

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "grammar_points" in msg and msg["grammar_points"]:
            st.caption(f"Grammar points: {', '.join(msg['grammar_points'])}")

# Chat input
if prompt := st.chat_input("Ask a question about HSK1 Chinese..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Consulting curriculum..."):
            try:
                res = httpx.post(
                    f"{API_URL}/tutoring/chat",
                    json={"learner_id": st.session_state.learner_id, "message": prompt},
                    timeout=60.0,
                )
                if res.status_code == 200:
                    payload = res.json()
                    tutor_data = payload["response"]
                    st.markdown(tutor_data["reply"])
                    if tutor_data.get("suggested_practice"):
                        st.info(f"💡 Practice: {tutor_data['suggested_practice']}")
                    st.caption(f"Inference: `{payload['provider']}`")

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": tutor_data["reply"],
                            "grammar_points": tutor_data.get("grammar_points", []),
                        }
                    )
                else:
                    st.error(f"API Error {res.status_code}: {res.text}")
            except Exception as e:
                st.error(f"Could not connect to backend: {e}")
