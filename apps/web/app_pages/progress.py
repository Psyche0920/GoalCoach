"""Progress — mastery, spaced-retention, review schedule, and error profile."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from goalcoach_api import (
    concept_status,
    current_retention,
    fmt_dt,
    fmt_pct,
    get_learner,
    overall_progress,
)

learner_id = st.session_state.get("learner_id")
learner, error = get_learner(learner_id)

if error == "not_found":
    st.info(
        "No data yet — have your first tutor session on the **Tutor** tab and progress "
        "will appear here.",
        icon=":material/query_stats:",
    )
    st.stop()

if error:
    st.error(error, icon=":material/cloud_off:")
    st.stop()

mastery = learner.get("mastery") or {}
errors = learner.get("error_profile") or []

ops = st.container(border=True).columns(3, gap="medium")
ops[0].metric("Overall progress", fmt_pct(overall_progress(learner)), help="Concept-weighted, mastery-weighted, time-decayed")
ops[1].metric("Concepts tracked", len(mastery))
ops[2].metric("Recurring errors", len(errors))

if not mastery:
    st.caption("Open the **Tutor** tab to start practising and building your mastery map.")
    st.stop()

rows = []
for cid, item in mastery.items():
    retention = current_retention(
        float(item.get("retention_score", 1.0) or 1.0),
        item.get("last_reviewed_at"),
        decay_lambda=float(item.get("decay_lambda", 0.05) or 0.05),
    )
    status, _ = concept_status(item)
    rows.append(
        {
            "Concept": cid,
            "Mastery (%)": round(float(item.get("mastery_score", 0.0)) * 100),
            "Retention (%)": round(retention * 100),
            "Evidence": int(item.get("evidence_count", 0)),
            "Interval (days)": round(float(item.get("interval_days", 0)), 1),
            "Weight": float(item.get("weight", 1.0)),
            "Next review": fmt_dt(item.get("next_review_at")),
            "Status": status,
        }
    )
df = pd.DataFrame(rows).sort_values("Mastery (%)", ascending=False)

st.header("Mastery vs retention", divider="gray")
st.caption("Retention is decayed to *right now*; Mastery is the score at the last review.")

chart_df = df.melt(
    id_vars=["Concept"],
    value_vars=["Mastery (%)", "Retention (%)"],
    var_name="Metric",
    value_name="Score",
)
chart = (
    alt.Chart(chart_df)
    .mark_bar()
    .encode(
        x=alt.X("Concept:N", sort=list(df["Concept"]), axis=alt.Axis(labelAngle=-45)),
        y=alt.Y("Score:Q", title="Score (%)"),
        color=alt.Color(
            "Metric:N",
            scale=alt.Scale(domain=["Mastery (%)", "Retention (%)"], range=["#88c0d0", "#d08770"]),
        ),
        xOffset=alt.XOffset("Metric:N"),
    )
    .properties(height=320)
)
st.altair_chart(chart, width="stretch")

st.header("Concept table", divider="gray")
st.dataframe(
    df,
    column_config={
        "Concept": st.column_config.TextColumn("Concept"),
        "Mastery (%)": st.column_config.NumberColumn("Mastery", format="%d%%"),
        "Retention (%)": st.column_config.NumberColumn("Retention now", format="%d%%"),
        "Evidence": st.column_config.NumberColumn("Evidence", format="%d"),
        "Interval (days)": st.column_config.NumberColumn("Interval", format="%g d"),
        "Weight": st.column_config.NumberColumn("Weight", format="%.2f"),
        "Next review": st.column_config.TextColumn("Next review"),
        "Status": st.column_config.TextColumn("Status"),
    },
    hide_index=True,
    width="stretch",
)

st.header("Review schedule", divider="gray")
schedule = df[["Concept", "Retention (%)", "Next review", "Status"]].sort_values(
    "Retention (%)"
)
st.dataframe(
    schedule,
    column_config={
        "Concept": st.column_config.TextColumn("Concept"),
        "Retention (%)": st.column_config.NumberColumn("Retention now", format="%d%%"),
        "Next review": st.column_config.TextColumn("Next review"),
        "Status": st.column_config.TextColumn("Status"),
    },
    hide_index=True,
    width="stretch",
)

st.header("Error profile", divider="gray")
if errors:
    err_rows = [
        {
            "Code": record.get("code", ""),
            "Concept": record.get("concept_id", ""),
            "Occurrences": record.get("occurrences", 1),
            "Last seen": fmt_dt(record.get("last_seen_at")),
            "Examples": " · ".join(str(e) for e in (record.get("examples") or [])[:3]),
        }
        for record in errors
    ]
    st.dataframe(
        pd.DataFrame(err_rows).sort_values("Occurrences", ascending=False),
        column_config={
            "Code": st.column_config.TextColumn("Code"),
            "Concept": st.column_config.TextColumn("Concept"),
            "Occurrences": st.column_config.NumberColumn("Occurrences", format="%d"),
            "Last seen": st.column_config.TextColumn("Last seen"),
            "Examples": st.column_config.TextColumn("Examples"),
        },
        hide_index=True,
        width="stretch",
    )
else:
    st.caption("No recurring errors recorded yet. Nice and clean.")

st.caption("Retention math matches the backend: R = R₀ · e^(−λ · days since last review).")