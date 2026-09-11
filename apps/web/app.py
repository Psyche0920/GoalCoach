"""GoalCoach — Streamlit learning-coach app.

Run with:
    uv run streamlit run apps/web/app.py

Multi-page app backed by the FastAPI REST API (default http://localhost:8000,
override with the GOALCOACH_API_URL environment variable).
"""

from __future__ import annotations

import streamlit as st

from goalcoach_api import backend_ok, new_learner_id


def _apply_learner_id() -> None:
    st.session_state.learner_id = st.session_state.learner_id_input


st.set_page_config(
    page_title="GoalCoach",
    page_icon="🐼",
    layout="wide",
)

if "learner_id" not in st.session_state:
    st.session_state.learner_id = new_learner_id()

pages = st.navigation(
    [
        st.Page("app_pages/home.py", title="Today", icon=":material/today:", default=True),
        st.Page("app_pages/plan.py", title="Daily plan", icon=":material/event_available:"),
        st.Page("app_pages/progress.py", title="Progress", icon=":material/query_stats:"),
        st.Page("app_pages/tutor.py", title="Tutor", icon=":material/forum:"),
    ],
    position="top",
)

with st.sidebar:
    st.markdown("## :material/pets: GoalCoach")
    st.caption("Your HSK learning coach")
    st.divider()

    st.markdown("### Learner")
    st.badge(
        "Backend online" if backend_ok() else "Backend offline",
        icon=":material/cloud_done:" if backend_ok() else ":material/cloud_off:",
        color="green" if backend_ok() else "red",
    )

    st.text_input(
        "Learner ID",
        value=st.session_state.learner_id,
        key="learner_id_input",
        on_change=_apply_learner_id,
        help="Every page speaks to the backend as this learner.",
    )
    if st.button(
        "New learner",
        key="new_learner_button",
        help="Generate a fresh learner ID and start a brand-new profile.",
        icon=":material/add_box:",
        width="stretch",
        type="primary",
    ):
        st.session_state.learner_id = new_learner_id()
        st.session_state.learner_id_input = st.session_state.learner_id
        st.toast("New learner ID generated", icon=":material/check:")
        st.rerun()
    st.caption("Resets your progress — use with care.")

st.title(f"{pages.icon} {pages.title}")

pages.run()