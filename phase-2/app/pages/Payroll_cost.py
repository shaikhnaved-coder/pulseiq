import duckdb, pandas as pd, streamlit as st, altair as alt

st.set_page_config(page_title="Payroll Cost", layout="wide")
st.title("Payroll Cost")

@st.cache_data
def q(sql):
    con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
    return con.execute(sql).df()

MIN_GROUP = 5
md = q("SELECT * FROM metrics.m30_payroll_month_dept")
tot = q("SELECT * FROM metrics.m31_payroll_month_total ORDER BY month_start_date")
exc = q("SELECT rule, reason, COUNT(*) AS rows, ROUND(SUM(gross_pay), 2) AS gross_pay FROM metrics.payroll_exclusions GROUP BY 1, 2")
for d in (md, tot):
    d["month_start_date"] = pd.to_datetime(d["month_start_date"])

with st.expander("How these numbers are defined (read first)"):
    st.markdown(f"""
- **Gross pay:** earned fixed pay + overtime + variable pay. **Net pay:** gross pay minus employee deductions.
- **Employer cost:** gross pay + employer PF + employer ESI.
- **Cost per employee:** employer cost divided by the number of employees paid in the month.
- **Only totals and averages are shown.** Any department and month group with fewer than {MIN_GROUP} people is hidden.
""")
if len(exc):
    st.warning("Rows excluded from every number on this page because they are bad data:")
    st.dataframe(exc.rename(columns={"rule": "Rule", "reason": "Why", "rows": "Rows", "gross_pay": "Gross pay removed"}),
                 use_container_width=True, hide_index=True)
else:
    st.info("No rows are excluded at the moment. Every payroll row is included.")

depts = sorted(md["department"].unique())
sel = st.multiselect("Department", depts, default=depts)
measure = st.radio("Measure", ["Employer cost", "Gross pay", "Net pay"], horizontal=True)
col = {"Employer cost": "employer_cost", "Gross pay": "gross_pay", "Net pay": "net_pay"}[measure]
mdf = md[md["department"].isin(sel)]

c = st.columns(5)
c[0].metric("Gross pay (company)", f"{tot['gross_pay'].sum() / 1e6:,.1f} M")
c[1].metric("Net pay (company)", f"{tot['net_pay'].sum() / 1e6:,.1f} M")
c[2].metric("Employer cost (company)", f"{tot['employer_cost'].sum() / 1e6:,.1f} M")
c[3].metric("Months", f"{len(tot)}")
c[4].metric("Avg monthly cost per employee", f"{tot['employer_cost'].sum() / tot['group_size'].sum():,.0f}")
dept_sum = md["employer_cost"].sum()
st.caption(f"Company totals include every department. Department charts hide groups under {MIN_GROUP} people, so they add up to "
           f"{(tot['employer_cost'].sum() - dept_sum) / 1e6:,.2f} M less in employer cost. That gap is the hidden small group.")

st.header("Trend")
t1, t2 = st.columns(2)
t1.subheader("Company cost by month")
long = tot.melt(id_vars="month_start_date", value_vars=["gross_pay", "net_pay", "employer_cost"],
                var_name="measure", value_name="amount")
t1.altair_chart(alt.Chart(long).mark_line(point=True).encode(
    x=alt.X("month_start_date:T", title="Month"), y=alt.Y("amount:Q", title="Amount"),
    color=alt.Color("measure:N", title=""), tooltip=["month_start_date:T", "measure", "amount"]).properties(height=300),
    use_container_width=True)
t2.subheader("Cost per employee by month")
t2.altair_chart(alt.Chart(tot).mark_line(point=True, color="#e0a030").encode(
    x=alt.X("month_start_date:T", title="Month"),
    y=alt.Y("cost_per_employee:Q", title="Employer cost per employee", scale=alt.Scale(zero=False)),
    tooltip=["month_start_date:T", "cost_per_employee"]).properties(height=300), use_container_width=True)

st.header(f"{measure} by department")
bd = (mdf.groupby("department", as_index=False)
      .agg(amount=(col, "sum"), employer_cost=("employer_cost", "sum"), employee_months=("group_size", "sum")))
bd["cost_per_employee"] = (bd["employer_cost"] / bd["employee_months"]).round(0)
st.altair_chart(alt.Chart(bd).mark_bar(color="#4f81bd").encode(
    x=alt.X("amount:Q", title=measure), y=alt.Y("department:N", sort="-x", title="", axis=alt.Axis(labelLimit=300)),
    tooltip=["department", "amount"]).properties(height=380, padding={"left": 40}), use_container_width=True)

st.header(f"{measure} by department and month")
hm = mdf.assign(value=mdf[col])
st.altair_chart(alt.Chart(hm).mark_rect().encode(
    x=alt.X("month_start_date:T", title="Month", timeUnit="yearmonth"),
    y=alt.Y("department:N", title="", axis=alt.Axis(labelLimit=300)),
    color=alt.Color("value:Q", title=measure, scale=alt.Scale(scheme="blues")),
    tooltip=["month_start_date:T", "department", "value"]).properties(height=380, padding={"left": 40}),
    use_container_width=True)

st.header("Cost per employee by department")
st.dataframe(bd.sort_values("cost_per_employee", ascending=False)[["department", "cost_per_employee", "employee_months"]]
             .rename(columns={"department": "Department", "cost_per_employee": "Avg monthly cost per employee",
                              "employee_months": "Employee-months"}), use_container_width=True, hide_index=True)

st.header("Trend by department")
dl = mdf[mdf["department"].isin(sel)]
st.altair_chart(alt.Chart(dl).mark_line().encode(
    x=alt.X("month_start_date:T", title="Month"),
    y=alt.Y("cost_per_employee:Q", title="Cost per employee", scale=alt.Scale(zero=False)),
    color=alt.Color("department:N", title=""), tooltip=["month_start_date:T", "department", "cost_per_employee"]
).properties(height=340), use_container_width=True)