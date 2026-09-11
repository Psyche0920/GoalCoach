"""Today — learner dashboard: honest progress, review queue, and today's plan."""

from __future__ import annotations

import streamlit as st

from goalcoach_api import (
    fmt_pct,
    generate_plan,
    get_learner,
    goal_summary,
    is_review_due,
    kind_meta,
    overall_progress,
    send_chat,
)

learner_id = st.session_state.get("learner_id")
learner, error = get_learner(learner_id)

if error == "not_found":
    st.subheader("Your coach profile is not created yet")
    with st.container(border=True):
        st.markdown(
            "GoalCoach tracks your HSK progress, plans your daily study session, and "
            "remembers what you practise. Everything keys off a learner profile."
        )
        st.markdown(
            "Your profile is created automatically the first time you talk to your tutor "
            "on the **Tutor** tab. Or create it now with the default HSK1 goal:"
        )
        if st.button(
            "Create profile and set an HSK1 goal",
            icon=":material/person_add:",
            type="primary",
        ):
            _, chat_error = send_chat(learner_id, "你好！")
            if chat_error:
                st.error(chat_error, icon=":material/error:")
            else:
                st.toast("Profile created with an HSK1 goal", icon=":material/check:")
                st.rerun()
    st.stop()

if error:
    st.error(error, icon=":material/cloud_off:")
    st.stop()

st.caption("Your honest, time-decayed progress at a glance")

mastery = learner.get("mastery") or {}
errors = learner.get("error_profile") or []
plan = learner.get("active_plan")
goal = learner.get("goal") or {}

st.subheader(":material/flag: Your goal")
st.caption("Created for you when your tutor session begins")
st.markdown(f"**{goal_summary(learner)}**")

if goal.get("target_date"):
    st.caption(f"Target date: {goal['target_date']}")

progress = overall_progress(learner)
practiced = sum(1 for item in mastery.values() if item.get("evidence_count", 0) > 0)
due_now = [cid for cid in mastery if is_review_due(mastery[cid])]

cols = st.columns(4, gap="medium", vertical_alignment="center")
with cols[0].container(border=True):
    st.metric("Overall progress", fmt_pct(progress), help="Concept-weighted and time-decayed")
with cols[1].container(border=True):
    st.metric("Concepts practised", f"{practiced} / {len(mastery)}")
with cols[2].container(border=True):
    st.metric("Due for review", len(due_now), help="Concepts whose next review is due")
with cols[3].container(border=True):
    st.metric("Recurring errors", len(errors))

with st.expander("Why this number is honest", icon=":material/info:"):
    st.markdown(
        "Progress is **concept-weighted, mastery-weighted, and time-decayed**: "
        "`progress = Σ(weight × mastery × current_retention) / Σ(weight)`. "
        "A concept you reviewed yesterday but haven't touched for a month counts for "
        "less today — retention decays exponentially since your last review, exactly "
        "as the backend computes it."
    )

st.header("Today's plan", divider="gray")
if plan:
    available = int(goal.get("daily_available_minutes") or 20)
    budget = sum(item.get("estimated_minutes", 0) or 0 for item in plan.get("items", []))
    st.badge(f"Status: {plan.get('status', 'active').title()}", icon=":material/event:")
    st.progress(min(1.0, budget / max(1, available)), text=f"Planned {budget} min of {available} min available")
    for item in plan["items"]:
        label, color = kind_meta(item.get("kind"))
        with st.container(border=True):
            head = st.columns([1, 1])
            head[0].markdown(f"**:{color}-badge[{label}]** {item.get('objective') or ''}")
            head[1].markdown(
                f"<div style='text-align:right'>{item.get('estimated_minutes')} min "
                f"{':material/check_circle:' if item.get('completed') else ''}</div>",
                unsafe_allow_html=True,
            )
    if st.button("Regenerate today's plan", icon=":material/refresh:", width="stretch"):
        _, regen_error = generate_plan(learner_id)
        if regen_error:
            st.error(regen_error, icon=":material/error:")
        else:
            st.toast("Plan regenerated", icon=":material/refresh:")
            st.rerun()
else:
    st.info(
        "No active plan yet. Generate a fresh plan for today — it adapts to your current "
        "mastery and due reviews.",
        icon=":material/event_available:",
    )
    if st.button("Generate today's plan", icon=":material/play_arrow:", type="primary"):
        plan_result, plan_error = generate_plan(learner_id)
        if plan_error:
            st.error(plan_error, icon=":material/error:")
        else:
            st.toast("Plan created", icon=":material/check:")
            st.rerun()

st.header("Review queue", divider="gray")
if due_now:
    st.markdown(
        "Needs a spaced review soon: **"
        + ", ".join(f"`{cid}`" for cid in due_now[:8])
        + "**" + ("…" if len(due_now) > 8 else "")
    )
else:
    st.caption("Nothing overdue right now. 保持！")

st.header("Recurring errors", divider="gray")
if errors:
    for record in errors[:4]:
        with st.container(border=True):
            st.markdown(f"**`{record.get('code') or '?'}`** — seen {record.get('occurrences', 1)}×")
            st.caption(record.get("concept_id", ""))
            if record.get("examples"):
                st.markdown("Example: " + " · ".join(str(e) for e in record["examples"][:3]))
else:
    st.caption("No recurring errors recorded yet. Great start!")