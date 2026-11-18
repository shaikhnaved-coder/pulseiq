from db import get_connection
import duckdb, pandas as pd, streamlit as st, altair as alt

st.set_page_config(page_title="Attendance & Leave", layout="wide")
st.title("Attendance and Leave Trends")

@st.cache_data
def q(sql):
    con = get_connection()
    return con.sql(sql).df()

att = q("SELECT * FROM wh.v_attendance_monthly")
leave = q("SELECT * FROM wh.v_leave_monthly")
hol = q("SELECT * FROM wh.v_holiday_months")

depts = sorted(att["department"].unique())
sel = st.multiselect("Department", depts, default=depts)
att_f = att[att["department"].isin(sel)]
leave_f = leave[leave["department"].isin(sel)]

# KPIs
overall_rate = 100 * att_f["present_days"].sum() / att_f["scheduled_days"].sum()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Attendance rate", f"{overall_rate:.1f}%")
c2.metric("Late arrivals", f"{int(att_f['late_arrivals'].sum()):,}")
c3.metric("Overtime hours", f"{att_f['overtime_hours'].sum():,.0f}")
c4.metric("Leave days", f"{int(leave_f['leave_days'].sum()):,}")

# Holiday months to shade/mark on the chart
hol_marks = hol[hol["holidays"] > 0].copy()
hol_marks["label"] = hol_marks.apply(
    lambda r: f"{int(r.holidays)} holiday(s)" + (f", {int(r.long_weekends)} long wknd" if r.long_weekends else ""), axis=1)

# 1) Attendance rate by month x department
st.subheader("Attendance rate by month and department")
line = alt.Chart(att_f).mark_line(point=True).encode(
    x=alt.X("month:T", title="Month"),
    y=alt.Y("attendance_rate:Q", title="Attendance rate (%)", scale=alt.Scale(zero=False)),
    color="department:N",
    tooltip=["month:T", "department", "attendance_rate"])
marks = alt.Chart(hol_marks).mark_rule(color="orange", strokeDash=[4, 4], opacity=0.6).encode(
    x="month:T", tooltip=["month:T", "label", "holiday_dates"])
st.altair_chart((marks + line).properties(height=380), use_container_width=True)
st.caption("Orange dashed lines = months with holidays. Hover to see which dates and any long weekends.")

# 2) Holiday table
st.subheader("Holidays and long weekends")
st.dataframe(hol_marks[["month", "holidays", "long_weekends", "working_days", "holiday_dates"]]
             .rename(columns={"holidays": "Holidays", "long_weekends": "Mon/Fri holidays (long weekend)",
                              "working_days": "Working days", "holiday_dates": "Dates"}),
             use_container_width=True)

# 3) Late arrivals and overtime
m = att_f.groupby("month", as_index=False)[["late_arrivals", "overtime_hours"]].sum()
a, b = st.columns(2)
a.subheader("Late arrivals by month")
a.altair_chart(alt.Chart(m).mark_bar().encode(x="month:T", y="late_arrivals:Q",
               tooltip=["month:T", "late_arrivals"]), use_container_width=True)
b.subheader("Overtime hours by month")
b.altair_chart(alt.Chart(m).mark_bar(color="#e07b39").encode(x="month:T", y="overtime_hours:Q",
               tooltip=["month:T", "overtime_hours"]), use_container_width=True)

# 4) Leave days by type
st.subheader("Leave days by type")
st.altair_chart(alt.Chart(leave_f).mark_bar().encode(
    x="month:T", y=alt.Y("sum(leave_days):Q", title="Leave days"), color="leave_type:N",
    tooltip=["month:T", "leave_type:N", "sum(leave_days):Q"]).properties(height=320),
    use_container_width=True)

 # 5) Unusual months
st.subheader("Unusual months")

def pct(x, base):
    return 100 * (x - base) / base if base else 0

t = att_f.groupby("month", as_index=False).agg(
    sched=("scheduled_days", "sum"), pres=("present_days", "sum"),
    late=("late_arrivals", "sum"), ot=("overtime_hours", "sum"))
t["attendance_rate"] = 100 * t["pres"] / t["sched"]
lv = leave_f.groupby("month", as_index=False)["leave_days"].sum()
t = (t.merge(lv, on="month", how="left")
      .merge(hol[["month", "holidays", "long_weekends", "holiday_dates"]], on="month", how="left"))
t[["leave_days", "holidays", "long_weekends"]] = t[["leave_days", "holidays", "long_weekends"]].fillna(0)
t["holiday_dates"] = t["holiday_dates"].fillna("none")
t["z_score"] = (t["attendance_rate"] - t["attendance_rate"].mean()) / t["attendance_rate"].std()

top3 = t.reindex(t["z_score"].abs().sort_values(ascending=False).index).head(3)
avg = t[["attendance_rate", "late", "ot", "leave_days"]].mean()

st.dataframe(top3[["month", "attendance_rate", "z_score", "late", "ot", "leave_days",
                   "holidays", "long_weekends"]].round(2), use_container_width=True)

st.markdown("**Three unusual months and what likely caused them**")
for _, r in top3.iterrows():
    d_leave = pct(r.leave_days, avg.leave_days)
    d_late = pct(r.late, avg.late)
    d_ot = pct(r.ot, avg.ot)
    gap = r.attendance_rate - avg.attendance_rate
    direction = "below" if gap < 0 else "above"
    if gap < 0:
        if d_leave > 15 and r.holidays > 0:
            cause = "a leave spike around the holidays and long weekends"
        elif d_leave > 15:
            cause = "a leave spike with no holiday to explain it"
        elif d_late > 15:
            cause = "a rise in late arrivals"
        else:
            cause = "no single driver in leave, lateness or overtime; check unpaid absence"
    else:
        cause = "low leave and a full working month" if d_leave < -15 else "a normal month with steady attendance"
    hol_txt = f"{int(r.holidays)} holiday(s): {r.holiday_dates}" if r.holidays > 0 else "no holidays"
    if r.long_weekends > 0:
        hol_txt += f", including {int(r.long_weekends)} long weekend"
    st.markdown(
        f"- **{r.month:%B %Y}**: attendance {r.attendance_rate:.1f}% "
        f"({abs(gap):.1f} pts {direction} the {avg.attendance_rate:.1f}% average). "
        f"Leave days {d_leave:+.0f}%, late arrivals {d_late:+.0f}%, overtime {d_ot:+.0f}% "
        f"vs the monthly average; {hol_txt}. Likely caused by {cause}.")

# 6) Three insights with numbers
st.subheader("Insights")
overall_rate = 100 * att_f["present_days"].sum() / att_f["scheduled_days"].sum()
dept_rate = (att_f.groupby("department")[["present_days", "scheduled_days"]].sum()
             .assign(r=lambda d: 100 * d.present_days / d.scheduled_days).sort_values("r"))
m = att_f.groupby("month", as_index=False)[["late_arrivals", "overtime_hours"]].sum()
late_peak = m.loc[m["late_arrivals"].idxmax()]
late_avg = m["late_arrivals"].mean()
top_leave = leave_f.groupby("leave_type")["leave_days"].sum().sort_values(ascending=False)
st.markdown(f"""
1. **Department gap:** overall attendance is {overall_rate:.1f}%. {dept_rate.index[0]} is lowest at {dept_rate.r.iloc[0]:.1f}% and {dept_rate.index[-1]} highest at {dept_rate.r.iloc[-1]:.1f}%, a gap of {dept_rate.r.iloc[-1] - dept_rate.r.iloc[0]:.1f} points.
2. **Late arrival peak:** {late_peak['month']:%B %Y} had {int(late_peak['late_arrivals']):,} late arrivals, {pct(late_peak['late_arrivals'], late_avg):.0f}% above the monthly average of {late_avg:,.0f}.
3. **Leave mix:** {top_leave.index[0]} is the largest leave type with {int(top_leave.iloc[0]):,} days, {100 * top_leave.iloc[0] / top_leave.sum():.0f}% of all leave days.
""")