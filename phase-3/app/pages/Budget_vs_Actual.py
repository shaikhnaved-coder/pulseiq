from db import get_connection
import duckdb, pandas as pd, streamlit as st, altair as alt

st.set_page_config(page_title="Budget vs Actual", layout="wide")
st.title("Budget vs Actual and KPI Targets")

@st.cache_data
def q(sql):
    con = get_connection()
    return con.execute(sql).df()

COLORS = {"Green": "#2e9e5b", "Amber": "#f0a830", "Red": "#d64545", "Grey": "#b0b0b0"}

pv = q("SELECT * FROM metrics.v_payroll_budget_variance")
rk = q("SELECT * FROM metrics.v_overspend_rank ORDER BY rank_by_amount")
pv["month_start_date"] = pd.to_datetime(pv["month_start_date"])

with st.expander("How these numbers are defined (read first)"):
    st.markdown("""
- **Budget:** planned payroll cost for each department and month. **Actual:** employer cost from the payroll data (valid rows only).
- **Sign rule:** variance = actual minus budget. **Positive means overspend, negative means under budget.**
- **Variance %:** variance divided by budget, times 100.
- **Payroll traffic lights:** Green = at most 2% over budget (or under budget). Amber = more than 2% and up to 5% over. Red = more than 5% over. Grey = no actual payroll data.
- **Department D00 (Executive Office)** has a budget but no payroll rows, so it is shown in Grey and left out of totals and the ranking.
- **Thresholds are our own choice:** the dataset gives targets, not colour rules.
""")

# ---------- Headline numbers ----------
has = pv[pv["actual"].notna()]
b, a = has["budget"].sum(), has["actual"].sum()
c = st.columns(5)
c[0].metric("Budget (18 months)", f"{b / 1e6:,.1f} M")
c[1].metric("Actual (18 months)", f"{a / 1e6:,.1f} M")
c[2].metric("Variance", f"{(a - b) / 1e6:,.2f} M", f"{(a - b) * 100 / b:+.2f}%", delta_color="inverse")
c[3].metric("Red department-months", f"{(has['status'] == 'Red').sum()}")
c[4].metric("Amber department-months", f"{(has['status'] == 'Amber').sum()}")
st.caption("Totals cover the 10 departments that have payroll data (D00 excluded). Under budget is shown in green.")

# ---------- Traffic-light heatmap ----------
st.header("Payroll variance by department and month")
names = sorted(pv["department_name"].unique())
sel = st.multiselect("Department", names, default=names)
pf = pv[pv["department_name"].isin(sel)]
st.altair_chart(alt.Chart(pf).mark_rect().encode(
    x=alt.X("month_start_date:T", title="Month", timeUnit="yearmonth"),
    y=alt.Y("department_name:N", title="", axis=alt.Axis(labelLimit=300)),
    color=alt.Color("status:N", title="Status",
                    scale=alt.Scale(domain=list(COLORS), range=list(COLORS.values()))),
    tooltip=[alt.Tooltip("month_start_date:T", title="Month"), alt.Tooltip("department_name:N", title="Department"),
             alt.Tooltip("budget:Q", format=",.0f"), alt.Tooltip("actual:Q", format=",.0f"),
             alt.Tooltip("variance:Q", format=",.0f"), alt.Tooltip("variance_pct:Q", format=".2f", title="Variance %"),
             "status"]).properties(height=380, padding={"left": 40}), use_container_width=True)

# ---------- Ranking ----------
st.header("Departments ranked by overspend")
st.altair_chart(alt.Chart(rk).mark_bar().encode(
    x=alt.X("total_variance:Q", title="Total variance over 18 months (positive = overspend)"),
    y=alt.Y("department_name:N", sort="-x", title="", axis=alt.Axis(labelLimit=300)),
    color=alt.condition(alt.datum.total_variance > 0, alt.value(COLORS["Red"]), alt.value(COLORS["Green"])),
    tooltip=["department_name", alt.Tooltip("total_variance:Q", format=",.0f"),
             alt.Tooltip("variance_pct:Q", format=".2f")]).properties(height=380, padding={"left": 40}),
    use_container_width=True)
t1, t2 = rk.iloc[0], rk.iloc[1]
st.caption(f"Biggest overspend: {t1['department_name']} (+{t1['total_variance']:,.0f}, {t1['variance_pct']:.2f}% over budget) "
           f"then {t2['department_name']} (+{t2['total_variance']:,.0f}, {t2['variance_pct']:.2f}%). "
           f"Ranked by rupee amount; the percentage ranking is in the table.")
st.dataframe(rk[["rank_by_amount", "department_name", "total_budget", "total_actual", "total_variance",
                 "variance_pct", "rank_by_pct", "months_over_budget", "red_months", "amber_months"]]
             .rename(columns={"rank_by_amount": "Rank (amount)", "department_name": "Department",
                              "total_budget": "Budget", "total_actual": "Actual", "total_variance": "Variance",
                              "variance_pct": "Variance %", "rank_by_pct": "Rank (%)",
                              "months_over_budget": "Months over budget", "red_months": "Red months",
                              "amber_months": "Amber months"}).round(2),
             use_container_width=True, hide_index=True)

# ---------- Detail table ----------
st.header("Detail by department and month")
det = pf.assign(Month=pf["month_start_date"].dt.strftime("%Y-%m"))
st.dataframe(det[["Month", "department_id", "department_name", "budget", "actual", "variance", "variance_pct", "status"]]
             .rename(columns={"department_id": "Dept", "department_name": "Department", "budget": "Budget",
                              "actual": "Actual", "variance": "Variance", "variance_pct": "Variance %",
                              "status": "Status"}).round(2),
             use_container_width=True, hide_index=True)

# ---------- KPI vs target ----------
st.header("KPIs vs targets")
kp = q("SELECT * FROM metrics.v_kpi_variance")
kp["month_start_date"] = pd.to_datetime(kp["month_start_date"])
EMOJI = {"Green": "🟢", "Amber": "🟠", "Red": "🔴", "Grey": "⚪"}

with st.expander("How the KPI traffic lights work"):
    st.markdown("""
- **Variance = actual minus target.** For attendance and task completion, higher is better. For overtime share and monthly attrition, lower is better.
- **Green:** target met. **Attendance rate:** Amber = up to 2 percentage points below target, Red = more than 2 points below.
- **Overtime, attrition and task completion:** Amber = target missed by up to 10% of the target value, Red = missed by more than that.
- **Grey:** no target or no actual. Department D00 has no KPI targets. D10 has no task completion target and no sprint data.
- **Attrition is hidden when the team is under 10 people** (from the attrition metric in Task 7), so D10 shows Grey in many months.
- **Small teams swing a lot:** one exit in a 20-person team is 5% attrition against a 1% target, so attrition shows many Reds.
- Task completion is rolled up from sprint level to month using a weighted average (weighted by number of tasks).
- **Thresholds are our own choice:** the dataset gives targets, not colour rules.
""")

kpis = ["Attendance rate", "Overtime share %", "Monthly attrition %", "Task completion %"]
kpi = st.radio("KPI", kpis, horizontal=True)
kf = kp[kp["kpi"] == kpi]

st.subheader(f"{kpi}: status by department and month")
st.altair_chart(alt.Chart(kf).mark_rect().encode(
    x=alt.X("month_start_date:T", title="Month", timeUnit="yearmonth"),
    y=alt.Y("department_name:N", title="", axis=alt.Axis(labelLimit=300)),
    color=alt.Color("status:N", title="Status",
                    scale=alt.Scale(domain=list(COLORS), range=list(COLORS.values()))),
    tooltip=[alt.Tooltip("month_start_date:T", title="Month"), alt.Tooltip("department_name:N", title="Department"),
             alt.Tooltip("target:Q", format=".3f"), alt.Tooltip("actual:Q", format=".3f"),
             alt.Tooltip("variance:Q", format=".3f"), "status"]).properties(height=340, padding={"left": 40}),
    use_container_width=True)

st.subheader("How many department-months in each status, by KPI")
st.altair_chart(alt.Chart(kp).mark_bar().encode(
    x=alt.X("count():Q", title="Department-months"),
    y=alt.Y("kpi:N", title="", axis=alt.Axis(labelLimit=300)),
    color=alt.Color("status:N", title="Status",
                    scale=alt.Scale(domain=list(COLORS), range=list(COLORS.values()))),
    tooltip=["kpi", "status", "count()"]).properties(height=220, padding={"left": 40}),
    use_container_width=True)

last = kp["month_start_date"].max()
st.subheader(f"Scorecard for the latest month ({last:%b %Y})")
lt = kp[kp["month_start_date"] == last].copy()
lt["s"] = lt["status"].map(EMOJI) + " " + lt["status"]
sc = (lt.pivot(index="department_name", columns="kpi", values="s")
        .reset_index().rename(columns={"department_name": "Department"}))
st.dataframe(sc, use_container_width=True, hide_index=True)
st.caption("D00 has no KPI targets, so it does not appear in the KPI section.")

# ---------- Verification ----------
st.header("Verification by hand")
st.markdown("""
Three department-months were recomputed outside the dashboard: the individual payroll rows were added up
(gross pay + employer PF + employer ESI), the budget was taken from the raw budget file, and variance was worked out
with a calculator. All three match the detail table above.
""")
ver = pd.DataFrame({
    "Department": ["Sales (D04)", "Data & AI (D03)", "Engineering (D01)"],
    "Month": ["2025-04", "2025-10", "2025-04"],
    "Budget": [5481000, 6070000, 23340000],
    "Actual (by hand)": [5885879.82, 6315814.86, 21428108.75],
    "Variance (by hand)": [404879.82, 245814.86, -1911891.25],
    "Variance % (by hand)": [7.39, 4.05, -8.19],
    "Status": ["Red", "Amber", "Green"],
    "Matches page": ["Yes", "Yes", "Yes"],
})
st.dataframe(ver, use_container_width=True, hide_index=True)

# ---------- Recommendations ----------
st.header("Recommendations for the two biggest overspenders")
st.caption("Based on patterns in the monthly numbers. The causes should be confirmed with Finance and the department heads.")

r1, r2 = st.columns(2)
with r1:
    st.subheader("1. Data & AI (+992,768, 0.90% over)")
    st.markdown("""
**What the numbers show**
- Over budget in 10 of 18 months, with 4 Red months: Sep 2025, Dec 2025, Mar 2026 and Jun 2026. These are all quarter-end months.
- Headcount is flat (47 to 54 people) and overtime pay is zero. Fixed pay barely moves from month to month, but the **budget dips in those quarter-end months**. In Jun 2026 the budget fell from 6.29 M to 5.48 M while fixed pay stayed near 6.0 M.
- Cost per employee stepped up about 10% from April 2026 (about 113 k to about 124 k).

**Recommendation**
1. Re-phase the budget so quarter-end months are not set below the steady fixed-pay run-rate (about 5.4 M to 6.3 M a month).
2. Build the April 2026 pay step-up into the next budget instead of treating it as a surprise.
3. Ask Finance whether the quarter-end dips were intentional (for example planned vacancies). If so, check whether those roles were filled.
""")
with r2:
    st.subheader("2. Product & Design (+608,352, 0.87% over)")
    st.markdown("""
**What the numbers show**
- Over budget in 12 of 18 months, but only 2 Red months: May 2025 (+8.7%) and Oct 2025 (+5.2%).
- Both headcount (23 to 26 or 27 people) and cost per employee (about 146 k to about 161 k, roughly +10%) rose.
- May 2025: the budget dropped from 5.29 M (a month with variable pay) to 3.09 M while fixed pay stayed at 3.32 M.
- Oct 2025: fixed pay was on budget, and the overspend matches a 150 k variable-pay payout.
- **It is converging:** the last 4 months are Green and net to about +2 k.

**Recommendation**
1. Budget variable-pay payouts in the month they are paid, so one-off bonuses do not show as overspend.
2. Set the budget from the approved headcount plan and current pay levels, since both have moved up.
3. Keep monthly tracking. No cost action looks needed now, because the run-rate is back on budget.
""")

    # ---------- Verification ----------
st.header("Verification by hand")
st.markdown("""
Three department-months were recomputed outside the dashboard: the individual payroll rows were added up
(gross pay + employer PF + employer ESI), the budget was taken from the raw budget file, and variance was worked out
with a calculator. All three match the detail table above.
""")
ver = pd.DataFrame({
    "Department": ["Sales (D04)", "Data & AI (D03)", "Engineering (D01)"],
    "Month": ["2025-04", "2025-10", "2025-04"],
    "Budget": [5481000, 6070000, 23340000],
    "Actual (by hand)": [5885879.82, 6315814.86, 21428108.75],
    "Variance (by hand)": [404879.82, 245814.86, -1911891.25],
    "Variance % (by hand)": [7.39, 4.05, -8.19],
    "Status": ["Red", "Amber", "Green"],
    "Matches page": ["Yes", "Yes", "Yes"],
})
st.dataframe(ver, use_container_width=True, hide_index=True)

# ---------- Recommendations ----------
st.header("Recommendations for the two biggest overspenders")
st.caption("Based on patterns in the monthly numbers. The causes should be confirmed with Finance and the department heads.")

r1, r2 = st.columns(2)
with r1:
    st.subheader("1. Data & AI (+992,768, 0.90% over)")
    st.markdown("""
**What the numbers show**
- Over budget in 10 of 18 months, with 4 Red months: Sep 2025, Dec 2025, Mar 2026 and Jun 2026. These are all quarter-end months.
- Headcount is flat (47 to 54 people) and overtime pay is zero. Fixed pay barely moves from month to month, but the **budget dips in those quarter-end months**. In Jun 2026 the budget fell from 6.29 M to 5.48 M while fixed pay stayed near 6.0 M.
- Cost per employee stepped up about 10% from April 2026 (about 113 k to about 124 k).

**Recommendation**
1. Re-phase the budget so quarter-end months are not set below the steady fixed-pay run-rate (about 5.4 M to 6.3 M a month).
2. Build the April 2026 pay step-up into the next budget instead of treating it as a surprise.
3. Ask Finance whether the quarter-end dips were intentional (for example planned vacancies). If so, check whether those roles were filled.
""")
with r2:
    st.subheader("2. Product & Design (+608,352, 0.87% over)")
    st.markdown("""
**What the numbers show**
- Over budget in 12 of 18 months, but only 2 Red months: May 2025 (+8.7%) and Oct 2025 (+5.2%).
- Both headcount (23 to 26 or 27 people) and cost per employee (about 146 k to about 161 k, roughly +10%) rose.
- May 2025: the budget dropped from 5.29 M (a month with variable pay) to 3.09 M while fixed pay stayed at 3.32 M.
- Oct 2025: fixed pay was on budget, and the overspend matches a 150 k variable-pay payout.
- **It is converging:** the last 4 months are Green and net to about +2 k.

**Recommendation**
1. Budget variable-pay payouts in the month they are paid, so one-off bonuses do not show as overspend.
2. Set the budget from the approved headcount plan and current pay levels, since both have moved up.
3. Keep monthly tracking. No cost action looks needed now, because the run-rate is back on budget.
""")