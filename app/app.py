import plotly.express as px
import pandas as pd
import streamlit as st
from db import query

st.set_page_config(page_title="PulseIQ", layout="wide")
st.title("PulseIQ: Workforce and headcount")

# ---------- load data (metric views only) ----------
names = query("SELECT department_id, department_name FROM metrics.lookup_department")
headcount = query("SELECT month_start_date, department_id, headcount FROM metrics.m01_headcount")
hires = query("SELECT month_start_date, department_id, hires FROM metrics.m02_hires")
attrition = query("""
    SELECT month_start_date, department_id, attrition_12m_pct, group_size
    FROM metrics.m05_attrition_rolling12
""")

headcount = headcount.merge(names, on="department_id")
hires = hires.merge(names, on="department_id")
attrition = attrition.merge(names, on="department_id")

# ---------- filters in the left sidebar ----------
st.sidebar.header("Filters")

all_depts = sorted(headcount["department_name"].unique())
chosen = st.sidebar.multiselect("Department", all_depts, default=all_depts)

months = [pd.Timestamp(m) for m in sorted(headcount["month_start_date"].unique())]
start, end = st.sidebar.select_slider(
    "Date range",
    options=months,
    value=(months[0], months[-1]),
    format_func=lambda m: m.strftime("%b %Y"),
)

if not chosen:
    st.warning("Pick at least one department in the sidebar.")
    st.stop()

# ---------- apply the filters ----------
in_depts = lambda df: df["department_name"].isin(chosen)
in_dates = lambda df: df["month_start_date"].between(start, end)

h = headcount[in_depts(headcount) & in_dates(headcount)]
hi = hires[in_depts(hires) & in_dates(hires)]
at_end = attrition[in_depts(attrition) & (attrition["month_start_date"] == end)]

# ---------- numbers for the cards ----------
total_end = h[h["month_start_date"] == end]["headcount"].sum()
total_start = h[h["month_start_date"] == start]["headcount"].sum()
hires_total = hi["hires"].sum()
depts_shown = h[h["month_start_date"] == end]["department_name"].nunique()

if len(at_end) > 0:
    # average of the department rates, weighted by how many people each department has
    attr = (at_end["attrition_12m_pct"] * at_end["group_size"]).sum() / at_end["group_size"].sum()
    attr_text = f"{attr:.1f}%"
else:
    attr_text = "n/a"

# ---------- KPI cards ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Headcount", f"{int(total_end):,}", f"{int(total_end - total_start):+,} since {start:%b %Y}")
c2.metric("Hires in period", f"{int(hires_total):,}")
c3.metric("Attrition, last 12 months", attr_text)
c4.metric("Departments shown", depts_shown)

st.caption(
    f"{start:%b %Y} to {end:%b %Y}. Groups with fewer than 5 people are hidden "
    "(this removes Executive Office, which has 1 person)."
)

# ---------- chart 1: headcount trend ----------
st.subheader("Headcount over time")

trend = h.groupby("month_start_date", as_index=False)["headcount"].sum()
fig = px.line(
    trend, x="month_start_date", y="headcount",
    labels={"month_start_date": "Month", "headcount": "People"},
)
st.plotly_chart(fig)

first, last = trend.iloc[0], trend.iloc[-1]
change_pct = 100 * (last["headcount"] - first["headcount"]) / first["headcount"]
st.markdown(
    f"**Insight:** Headcount went from {int(first['headcount']):,} in "
    f"{first['month_start_date']:%b %Y} to {int(last['headcount']):,} in "
    f"{last['month_start_date']:%b %Y}, a change of {change_pct:+.0f}%."
)

# ---------- chart 2: headcount by department ----------
st.subheader("Headcount by department")

dept = (
    h[h["month_start_date"] == end]
    .groupby("department_name", as_index=False)["headcount"].sum()
    .sort_values("headcount")
)
fig2 = px.bar(
    dept, x="headcount", y="department_name", orientation="h",
    labels={"headcount": "People", "department_name": ""},
)
st.plotly_chart(fig2)

top = dept.iloc[-1]
share = 100 * top["headcount"] / dept["headcount"].sum()
st.markdown(
    f"**Insight:** {top['department_name']} is the largest department with "
    f"{int(top['headcount'])} people, {share:.0f}% of the headcount shown ({end:%b %Y})."
)

# ---------- charts 3 and 4: where and how people work (today) ----------
st.subheader("Where and how people work")
st.caption("Today's staff. These two charts do not change with the filters.")

tier = query("SELECT city_tier, headcount FROM metrics.app_headcount_by_tier ORDER BY city_tier")
mode = query("SELECT work_mode, headcount FROM metrics.app_headcount_by_work_mode ORDER BY headcount DESC")

left, right = st.columns(2)

with left:
    fig3 = px.bar(
        tier, x="city_tier", y="headcount",
        labels={"city_tier": "City tier", "headcount": "People"},
    )
    st.plotly_chart(fig3)
    top_tier = tier.loc[tier["headcount"].idxmax()]
    tier_share = 100 * top_tier["headcount"] / tier["headcount"].sum()
    st.markdown(
        f"**Insight:** {top_tier['city_tier']} cities hold {int(top_tier['headcount'])} people, "
        f"{tier_share:.0f}% of the {int(tier['headcount'].sum())} employees."
    )

with right:
    fig4 = px.bar(
        mode, x="work_mode", y="headcount",
        labels={"work_mode": "Work mode", "headcount": "People"},
    )
    st.plotly_chart(fig4)
    top_mode = mode.loc[mode["headcount"].idxmax()]
    mode_share = 100 * top_mode["headcount"] / mode["headcount"].sum()
    st.markdown(
        f"**Insight:** {top_mode['work_mode']} is the most common work mode with "
        f"{int(top_mode['headcount'])} people, {mode_share:.0f}% of the {int(mode['headcount'].sum())} employees."
    )