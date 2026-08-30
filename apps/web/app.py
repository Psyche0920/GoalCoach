"""Minimal UI boundary; intentionally thin until the core loop is validated."""

import streamlit as st

st.set_page_config(page_title="GoalCoach", page_icon="🎯")
st.title("GoalCoach")
st.caption("Your adaptive HSK learning plan")
st.info("TODO(interface): connect the FastAPI daily-plan and progress endpoints.")
st.metric("Current progress", "—")
st.subheader("Today's plan")
st.write("No plan loaded yet.")
