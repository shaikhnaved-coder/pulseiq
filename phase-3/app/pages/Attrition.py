from db import get_connection
import duckdb, pandas as pd, streamlit as st, altair as alt

st.set_page_config(page_title="Attrition", layout="wide")
st.title("Attrition Analytics")

@st.cache_data
def q(sql):
    con = get_connection()
    return con.execute(sql).df()

def pct(x, base):
    return 100 * (x - base) / base if base else 0

# ---------- minimum group size rule (read from the metric catalog) ----------
def get_min_group():
    try:
        v = q("SELECT minimum_group_size FROM metrics.metric_catalog WHERE minimum_group_size IS NOT NULL")
        nums = pd.to_numeric(v["minimum_group_size"].astype(str).str.extract(r"(\d+)")[0], errors="coerce").dropna()
        return int(nums.mode().iloc[0]) if len(nums) else 5
    except Exception:
        return 5
MIN_GROUP = get_min_group()
st.caption(f"Privacy rule: groups smaller than {MIN_GROUP} people are hidden. No individual names or IDs are shown anywhere on this page.")

# =====================================================================
# SECTION 1: ACTUAL EXITS
# =====================================================================
st.header("Actual exits (what happened)")

m03 = q("""
    SELECT e.month_start_date AS month, COALESCE(d.department_name, e.department_id) AS department,
           e.exits, e.group_size
    FROM metrics.m03_exits e
    LEFT JOIN metrics.lookup_department d ON d.department_id = e.department_id
""")
m03["month"] = pd.to_datetime(m03["month"])
hidden = int((m03["group_size"] < MIN_GROUP).sum())
m03 = m03[m03["group_size"] >= MIN_GROUP]

depts = sorted(m03["department"].unique())
sel = st.multiselect("Department", depts, default=depts)
m03f = m03[m03["department"].isin(sel)]
if hidden:
    st.caption(f"{hidden} department-month rows hidden because the group was below {MIN_GROUP}.")

c1, c2, c3 = st.columns(3)
c1.metric("Total exits", f"{int(m03f['exits'].sum()):,}")
c2.metric("Avg exits per month", f"{m03f.groupby('month')['exits'].sum().mean():.1f}")
c3.metric("Months covered", f"{m03f['month'].nunique()}")

st.subheader("Exits per month")
by_month = m03f.groupby("month", as_index=False)["exits"].sum()
st.altair_chart(alt.Chart(by_month).mark_bar().encode(
    x=alt.X("month:T", title="Month"), y=alt.Y("exits:Q", title="Exits"),
    tooltip=["month:T", "exits"]).properties(height=300), use_container_width=True)

st.subheader("Exits per department")
by_dept = m03f.groupby("department", as_index=False)["exits"].sum().sort_values("exits", ascending=False)
st.altair_chart(alt.Chart(by_dept).mark_bar(color="#c0504d").encode(
    x=alt.X("exits:Q", title="Exits"), y=alt.Y("department:N", sort="-x", title=""),
    tooltip=["department", "exits"]).properties(height=320, padding={"left": 40}))

# ---------- tenure at exit + voluntary vs other ----------
ex = q("""
    WITH e AS (
        SELECT employee_id, department_id, hire_date, exit_date, employment_status
        FROM wh.dim_employee
        QUALIFY ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY valid_from DESC) = 1
    )
    SELECT COALESCE(d.department_name, e.department_id) AS department,
           e.employment_status,
           date_diff('day', e.hire_date, e.exit_date) / 365.25 AS tenure_years
    FROM e LEFT JOIN metrics.lookup_department d ON d.department_id = e.department_id
    WHERE e.exit_date IS NOT NULL AND e.hire_date IS NOT NULL
""")
ex["exit_type"] = ex["employment_status"].map(
    lambda s: "Voluntary (resigned)" if s == "Resigned" else "Other (terminated / contract ended)")
ex["tenure_band"] = pd.cut(ex["tenure_years"], [-0.01, 1, 2, 5, 10, 100],
                           labels=["Under 1 yr", "1-2 yrs", "2-5 yrs", "5-10 yrs", "10+ yrs"])
exf = ex[ex["department"].isin(sel)]

a, b = st.columns(2)
a.subheader("Tenure at exit")
ten = exf.groupby("tenure_band", observed=True, as_index=False).size().rename(columns={"size": "exits"})
ten = ten[ten["exits"] >= MIN_GROUP]
a.altair_chart(alt.Chart(ten).mark_bar(color="#4f81bd").encode(
    x=alt.X("tenure_band:N", sort=["Under 1 yr", "1-2 yrs", "2-5 yrs", "5-10 yrs", "10+ yrs"], 	title="Tenure when they left", axis=alt.Axis(labelAngle=0)),
    y="exits:Q", tooltip=["tenure_band", "exits"]), use_container_width=True)
a.caption(f"Median tenure at exit: {exf['tenure_years'].median():.1f} years. Bands under {MIN_GROUP} exits are hidden.")

b.subheader("Voluntary vs other exits")
typ = exf.groupby("exit_type", as_index=False).size().rename(columns={"size": "exits"})
typ = typ[typ["exits"] >= MIN_GROUP]
b.altair_chart(alt.Chart(typ).mark_bar().encode(
    x=alt.X("exits:Q", title="Exits"), y=alt.Y("exit_type:N", title="", sort="-x", axis=alt.Axis(labelLimit=320)),
    color=alt.Color("exit_type:N", legend=None), tooltip=["exit_type", "exits"]).properties(padding={"left": 40}), use_container_width=True)

st.subheader("Voluntary exit share by department")
vd = exf.groupby("department").agg(
    total=("exit_type", "size"),
    voluntary=("exit_type", lambda s: (s == "Voluntary (resigned)").sum())).reset_index()
vd = vd[vd["total"] >= MIN_GROUP]
vd["voluntary_pct"] = (100 * vd["voluntary"] / vd["total"]).round(1)
st.dataframe(vd.sort_values("voluntary_pct", ascending=False).rename(
    columns={"total": "Exits", "voluntary": "Voluntary", "voluntary_pct": "Voluntary %"}),
    use_container_width=True)

# =====================================================================
# SECTION 2: PREDICTED, NOT CERTAIN
# =====================================================================
st.divider()
st.header("Predicted, not certain")
st.warning("Everything in this section is a model PREDICTION about the next 12 months. It is not a record of what happened "
           "and it does not say who will leave. Shown by group only.")

risk_date = q("SELECT MAX(as_of_date) AS d FROM wh.fact_attrition_risk")["d"].iloc[0]
meta = q("SELECT DISTINCT model_version, model_note FROM wh.fact_attrition_risk")
st.caption(f"Prediction as of {pd.to_datetime(risk_date):%d %b %Y}. Model version: "
           f"{', '.join(meta['model_version'].dropna().astype(str).unique())}.")

m27 = q("""
    SELECT COALESCE(d.department_name, m.department_id) AS department, m.high_risk_pct, m.group_size
    FROM metrics.m27_high_risk_share m
    LEFT JOIN metrics.lookup_department d ON d.department_id = m.department_id
    WHERE m.as_of_date = (SELECT MAX(as_of_date) FROM metrics.m27_high_risk_share)
""")
m27 = m27[m27["group_size"] >= MIN_GROUP]
st.subheader("Predicted high-risk share by department")
st.altair_chart(alt.Chart(m27).mark_bar(color="#e0a030").encode(
    x=alt.X("high_risk_pct:Q", title="Predicted high-risk share (%)"),
    y=alt.Y("department:N", sort="-x", title=""),
    tooltip=["department", "high_risk_pct", "group_size"]).properties(height=320, padding={"left": 40}))

bands = q("""
    SELECT COALESCE(d.department_name, r.department_id) AS department, r.risk_band, COUNT(*) AS employees
    FROM wh.fact_attrition_risk r
    LEFT JOIN metrics.lookup_department d ON d.department_id = r.department_id
    WHERE r.as_of_date = (SELECT MAX(as_of_date) FROM wh.fact_attrition_risk)
    GROUP BY 1, 2
""")
tot = bands.groupby("department")["employees"].transform("sum")
bands = bands[tot >= MIN_GROUP]
st.subheader("Predicted risk bands by department (share of people)")
st.altair_chart(alt.Chart(bands).mark_bar().encode(
    x=alt.X("sum(employees):Q", stack="normalize", title="Share of department"),
    y=alt.Y("department:N", title=""), color="risk_band:N",
    tooltip=["department", "risk_band", "employees"]).properties(height=320, padding={"left": 40}))

reasons = q("""
    SELECT reason, COUNT(*) AS people FROM (
        SELECT top_reason_1 AS reason, risk_band, as_of_date FROM wh.fact_attrition_risk
        UNION ALL SELECT top_reason_2, risk_band, as_of_date FROM wh.fact_attrition_risk
        UNION ALL SELECT top_reason_3, risk_band, as_of_date FROM wh.fact_attrition_risk)
    WHERE UPPER(risk_band) LIKE 'HIGH%' AND reason IS NOT NULL
      AND as_of_date = (SELECT MAX(as_of_date) FROM wh.fact_attrition_risk)
    GROUP BY 1 ORDER BY 2 DESC
""")
reasons = reasons[reasons["people"] >= MIN_GROUP]
st.subheader("Most common predicted drivers among the high-risk group")
st.dataframe(reasons.rename(columns={"reason": "Driver the model pointed to", "people": "People in high-risk group"}),
             use_container_width=True)

st.info("""
**What this prediction is:** a statistical estimate of how likely groups of employees are to leave in the next 12 months,
based on patterns in past data. It helps teams decide where to look first, for example where to run stay conversations or fix workload.

**What it is not:** it is not a fact, not a verdict on any individual, and not a reason to treat anyone differently.
Some people marked high risk will stay and some marked low risk will leave. It is shown only for groups of at least
""" + str(MIN_GROUP) + """ people, never by name. Do not use it for hiring, firing, promotion or pay decisions.
""")

# =====================================================================
# 3 BIGGEST FINDINGS (actual data)
# =====================================================================
st.divider()
st.header("3 biggest findings (actual exits)")
top_d = by_dept.iloc[0]
share_top = 100 * top_d["exits"] / by_dept["exits"].sum()
pk = by_month.loc[by_month["exits"].idxmax()]
avg_m = by_month["exits"].mean()
early = 100 * (exf["tenure_years"] < 2).mean()
vol = 100 * (exf["exit_type"] == "Voluntary (resigned)").mean()
st.markdown(f"""
1. **{top_d['department']} loses the most people:** {int(top_d['exits']):,} exits, {share_top:.0f}% of all exits in the selected departments.
2. **{pk['month']:%B %Y} was the peak month:** {int(pk['exits'])} exits, {pct(pk['exits'], avg_m):.0f}% above the monthly average of {avg_m:.1f}.
3. **Exits happen early and are mostly voluntary:** {early:.0f}% of leavers had under 2 years of tenure (median {exf['tenure_years'].median():.1f} years), and {vol:.0f}% of all exits were resignations.
""")