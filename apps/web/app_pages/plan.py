"""Daily plan — the generated study schedule with item-by-item detail."""

from __future__ import annotations

import streamlit as st

from goalcoach_api import generate_plan, get_learner, goal_summary, kind_meta

learner_id = st.session_state.get("learner_id")
learner, error = get_learner(learner_id)

if error == "not_found":
    st.info(
        "No learner profile yet — send a message to your tutor on the **Tutor** tab to "
        "create one, then come back to generate a plan.",
        icon=":material/event_available:",
    )
    st.stop()

if error:
    st.error(error, icon=":material/cloud_off:")
    st.stop()

plan = learner.get("active_plan")
goal = learner.get("goal") or {}

if plan is None:
    st.subheader("No active plan")
    st.markdown(
        "Plans are generated fresh each day and adapt to your current mastery and due "
        "reviews. You have no active plan right now — generate today's."
    )
    if st.button("Generate today's plan", icon=":material/play_arrow:", type="primary"):
        plan_result, plan_error = generate_plan(learner_id)
        if plan_error:
            st.error(plan_error, icon=":material/error:")
        else:
            st.toast("Plan created", icon=":material/check:")
            st.rerun()
    st.stop()

st.caption(f"Learner {learner_id}")
st.markdown(f"**:material/flag: {goal_summary(learner)}**")

status = (plan.get("status") or "active").title()
st.badge(f"Status: {status}", icon=":material/event:", color="green" if status == "Active" else "orange")

date_label = plan.get("date", "")
if date_label:
    st.caption("Generated " + date_label)

budget = sum((item.get("estimated_minutes", 0) or 0) for item in plan.get("items", []))
available = int(goal.get("daily_available_minutes") or 20)
completed = sum(1 for item in plan.get("items", []) if item.get("completed"))
total = len(plan.get("items", []))

done_col, budget_col = st.columns(2)
done_col.metric("Completed", f"{completed} / {total}")
budget_col.metric("Planned time", f"{budget} min", delta=f"{budget - available:+d} vs {available} min budget")

for item in plan.get("items", []):
    label, color = kind_meta(item.get("kind"))
    with st.container(border=True):
        cols = st.columns([4, 1, 1])
        cols[0].markdown(f"**:{color}-badge[{label}]** {item.get('objective') or ''}")
        cols[1].markdown(f":material/schedule: {item.get('estimated_minutes')} min")
        cols[2].markdown(
            f":material/check_circle: Done" if item.get("completed") else ":material/circle_outlined: Pending"
        )
        st.caption(f"`{item.get('concept_id') or ''}`")

plan_col, actions_col = st.columns([3, 1])
with plan_col:
    with st.expander("Why this plan", icon=":material/tune:"):
        st.markdown(plan.get("rationale") or "No rationale recorded.")
with actions_col:
    if st.button("Regenerate", icon=":material/refresh:", width="stretch"):
        _, regen_error = generate_plan(learner_id)
        if regen_error:
            st.error(regen_error, icon=":material/error:")
        else:
            st.toast("Plan regenerated", icon=":material/refresh:")
            st.rerun()