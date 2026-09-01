"""Streamlit chat box to test the configured LLMs (.env) directly."""

import json

import httpx
import streamlit as st

from goalcoach.infrastructure.config import Settings

st.set_page_config(page_title="GoalCoach Chat Test", page_icon="🎯")
st.title("GoalCoach Chat Test")
st.caption("Streaming chat against a selected provider")

settings = Settings()


def candidates() -> list[tuple[str, str, str | None, str]]:
    endpoints = []
    if settings.llm_base_url and settings.llm_model:
        endpoints.append(
            (settings.llm_base_url, settings.llm_model, settings.llm_api_key, "OpenRouter")
        )
    if settings.fallback_llm_base_url and settings.fallback_llm_model:
        endpoints.append(
            (
                settings.fallback_llm_base_url,
                settings.fallback_llm_model,
                None,
                "Ollama",
            )
        )
    return endpoints


all_candidates = candidates()
options = []
for base_url, model, _, name in all_candidates:
    options.append(f"{name} — {model}")
options.insert(0, "Auto (first reachable)")

selection = st.sidebar.radio("LLM provider", options, key="llm_choice")
if selection == options[0]:
    targets = all_candidates
else:
    index = options.index(selection) - 1
    targets = [all_candidates[index]]
st.sidebar.metric("Selected", selection.split(" — ")[0])
st.sidebar.metric("Endpoint", targets[0][0] if targets else "none")

if not targets:
    st.error("No LLM configured. Set GOALCOACH_LLM_* and GOALCOACH_FALLBACK_LLM_* in .env.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


def stream_reply(messages: list[dict]) -> str:
    failures: list[str] = []
    for base_url, model, api_key, name in targets:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        try:
            with httpx.stream(
                "POST",
                base_url.rstrip("/") + "/chat/completions",
                headers=headers,
                json={"model": model, "messages": messages, "stream": True},
                timeout=120,
            ) as response:
                response.raise_for_status()
                with st.chat_message("assistant"):
                    placeholder = st.empty()
                    text = ""
                    for line in response.iter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            line = line[6:]
                        if line == "[DONE]":
                            break
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        delta = chunk["choices"][0].get("delta", {})
                        added = delta.get("content") or delta.get("reasoning") or ""
                        if added:
                            text += added
                            placeholder.markdown(text)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": text}
                    )
                    return text
        except httpx.HTTPError as exc:
            failures.append(f"{name} ({base_url} / {model}): {exc}")
    raise RuntimeError("All selected LLM endpoints failed: " + " | ".join(failures))


if prompt := st.chat_input("Chat with the model…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    try:
        stream_reply(st.session_state.messages)
    except RuntimeError as exc:
        st.error(str(exc))