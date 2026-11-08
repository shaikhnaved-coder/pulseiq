import os, duckdb, pandas as pd, altair as alt, streamlit as st
st.set_page_config(page_title="Cross-department impact", layout="wide")
con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
q = lambda sql: con.execute(sql).fetchdf()

st.title("Cross-department impact view")
st.info("**Grain:** one row per department and month (Apr 2025 to Sep 2026). Headcount, payroll, attendance, "
        "leave and exits are each aggregated to that grain first, then joined. Headcount = month-end. "
        "Payroll cost = employer cost, with the 4 bad rows in payroll_exclusions removed. "
        "Overtime cost = overtime pay. Leave days per head = leave days / headcount.")

df = q("SELECT * FROM metrics.v_dept_month_impact ORDER BY department_name, month")
depts = sorted(df["department_name"].dropna().unique())
pick = st.multiselect("Departments", depts, default=depts)
view = df[df["department_name"].isin(pick)]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Department-month rows", len(view))
c2.metric("Total payroll cost", f"{view['payroll_cost'].sum():,.0f}")
c3.metric("Total overtime cost", f"{view['overtime_cost'].sum():,.0f}")
c4.metric("Total exits", int(view["exits"].sum()))

st.subheader("1. Combined department-month table")
st.dataframe(view, use_container_width=True, hide_index=True)

st.subheader("2. Department comparison: cost, overtime and attrition")
dept = (view.groupby("department_name")
            .agg(total_cost=("payroll_cost", "sum"), overtime_cost=("overtime_cost", "sum"),
                 exits=("exits", "sum"), avg_headcount=("headcount", "mean"))
            .reset_index())
dept["attrition_pct"] = (100 * dept["exits"] / dept["avg_headcount"]).round(1)
order = dept.sort_values("total_cost", ascending=False)["department_name"].tolist()
st.caption("Bars = total payroll cost and overtime cost (left axis). Red line = exits as % of average headcount "
           "over the whole period (right axis).")

long = dept.melt(id_vars="department_name", value_vars=["total_cost", "overtime_cost"],
                 var_name="measure", value_name="amount")
bars = alt.Chart(long).mark_bar().encode(
    x=alt.X("department_name:N", sort=order, title=None), xOffset="measure:N",
    y=alt.Y("amount:Q", title="Cost (square-root scale so overtime is visible)", scale=alt.Scale(type="sqrt")),
    color=alt.Color("measure:N", title="Cost measure"),
    tooltip=["department_name", "measure", alt.Tooltip("amount:Q", format=",.0f")])
points = alt.Chart(dept).mark_point(color="red", size=120, filled=True).encode(
    x=alt.X("department_name:N", sort=order),
    y=alt.Y("attrition_pct:Q", title="Attrition % (whole period)", axis=alt.Axis(titleColor="red")),
    tooltip=["department_name", "attrition_pct"])
st.altair_chart(alt.layer(bars, points).resolve_scale(y="independent"), use_container_width=True)
st.dataframe(dept.sort_values("total_cost", ascending=False), use_container_width=True, hide_index=True)

st.subheader("3. Comparison with the reference summary")
if os.path.exists("docs/pq13_comparison_summary.csv"):
    st.dataframe(pd.read_csv("docs/pq13_comparison_summary.csv"), use_container_width=True, hide_index=True)
else:
    st.caption("Run src/compare_pq13.py (Step 4) to fill this table.")
if os.path.exists("docs/pq13_difference_notes.md"):
    st.markdown(open("docs/pq13_difference_notes.md", encoding="utf-8").read())