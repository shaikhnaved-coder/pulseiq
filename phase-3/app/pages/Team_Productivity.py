import duckdb, numpy as np, pandas as pd, streamlit as st, altair as alt

st.set_page_config(page_title="Team Productivity", layout="wide")
st.title("Team Productivity")

@st.cache_data
def q(sql):
    con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
    return con.execute(sql).df()

d = q("SELECT * FROM metrics.m29_team_sprint_delivery")
d["sprint_end_date"] = pd.to_datetime(d["sprint_end_date"])

def roll(df, by):
    g = df.groupby(by, as_index=False).agg(
        tasks_total=("tasks_total", "sum"), tasks_cancelled=("tasks_cancelled", "sum"),
        tasks_in_scope=("tasks_in_scope", "sum"), tasks_done=("tasks_done", "sum"),
        velocity_points=("velocity_points", "sum"), done_on_time=("done_on_time", "sum"),
        cycle_days_sum=("cycle_days_sum", "sum"), cycle_task_count=("cycle_task_count", "sum"),
        tasks_blocked=("tasks_blocked", "sum"), tasks_reopened=("tasks_reopened", "sum"))
    g["on_time_pct"] = (100 * g["done_on_time"] / g["tasks_done"].replace(0, np.nan)).round(1)
    g["avg_cycle_days"] = (g["cycle_days_sum"] / g["cycle_task_count"].replace(0, np.nan)).round(1)
    g["blocked_pct"] = (100 * g["tasks_blocked"] / g["tasks_in_scope"].replace(0, np.nan)).round(1)
    g["reopened_pct"] = (100 * g["tasks_reopened"] / g["tasks_in_scope"].replace(0, np.nan)).round(1)
    return g

# ---------------- rules ----------------
with st.expander("How these numbers are defined (read first)", expanded=False):
    st.markdown("""
- **Velocity:** story points of tasks with status *Done* in the sprint.
- **Cycle time:** average days from *started date* to *completed date*, Done tasks only.
- **On-time rate:** Done tasks completed on or before their due date, divided by all Done tasks.
- **Blocked work:** tasks whose status is *Blocked*. **Reopened work:** tasks reopened at least once.
""")
st.info("**Cancelled tasks rule:** cancelled tasks are excluded from velocity, cycle time, on-time rate and from the base "
        "of the blocked and reopened shares. They are not counted as late or as delivered. They are shown separately "
        "below so you can see how much planned work was dropped.")

# ---------------- selectors ----------------
teams = sorted(d["team_name"].unique())
sel_teams = st.multiselect("Teams", teams, default=teams)
sprint_order = (d[["sprint_name", "sprint_end_date"]].drop_duplicates()
                .sort_values("sprint_end_date", ascending=False)["sprint_name"].tolist())
sel_sprint = st.selectbox("Sprint", ["All sprints"] + sprint_order)

dt = d[d["team_name"].isin(sel_teams)]
ds = dt if sel_sprint == "All sprints" else dt[dt["sprint_name"] == sel_sprint]
label = "all sprints" if sel_sprint == "All sprints" else sel_sprint

tot = roll(ds.assign(_all=1), "_all").iloc[0]
c = st.columns(6)
c[0].metric("Velocity (points)", f"{int(tot.velocity_points):,}")
c[1].metric("Avg cycle time", f"{tot.avg_cycle_days:.1f} days")
c[2].metric("On-time rate", f"{tot.on_time_pct:.1f}%")
c[3].metric("Blocked tasks", f"{int(tot.tasks_blocked):,}")
c[4].metric("Reopened tasks", f"{int(tot.tasks_reopened):,}")
c[5].metric("Cancelled tasks", f"{int(tot.tasks_cancelled):,}")
st.caption(f"Showing {label}, {len(sel_teams)} team(s).")

# ---------------- per team ----------------
st.header(f"Per team ({label})")
bt = roll(ds, "team_name")
a, b, c3 = st.columns(3)
def team_bar(col, title, color):
    return alt.Chart(bt).mark_bar(color=color).encode(
        x=alt.X(f"{col}:Q", title=title, scale=alt.Scale(zero=(col == "velocity_points"))),
        y=alt.Y("team_name:N", sort="-x", title="", axis=alt.Axis(labelLimit=300)),
        tooltip=["team_name", col]).properties(height=420, padding={"left": 40})
a.subheader("Velocity"); a.altair_chart(team_bar("velocity_points", "Story points", "#4f81bd"), use_container_width=True)
b.subheader("On-time rate"); b.altair_chart(team_bar("on_time_pct", "On-time %", "#59a14f"), use_container_width=True)
c3.subheader("Cycle time"); c3.altair_chart(team_bar("avg_cycle_days", "Avg days", "#e0a030"), use_container_width=True)

# ---------------- per sprint ----------------
st.header("Per sprint (trend across sprints)")
bs = roll(dt, ["sprint_end_date", "sprint_name"]).sort_values("sprint_end_date")
def sprint_line(col, title, color):
    return alt.Chart(bs).mark_line(point=True, color=color).encode(
        x=alt.X("sprint_end_date:T", title="Sprint end"),
        y=alt.Y(f"{col}:Q", title=title, scale=alt.Scale(zero=False)),
        tooltip=["sprint_name", col]).properties(height=240)
s1, s2, s3 = st.columns(3)
s1.subheader("Velocity"); s1.altair_chart(sprint_line("velocity_points", "Story points", "#4f81bd"), use_container_width=True)
s2.subheader("On-time rate"); s2.altair_chart(sprint_line("on_time_pct", "On-time %", "#59a14f"), use_container_width=True)
s3.subheader("Cycle time"); s3.altair_chart(sprint_line("avg_cycle_days", "Avg days", "#e0a030"), use_container_width=True)

# ---------------- blocked and reopened ----------------
st.header(f"Blocked and reopened work ({label})")
bl = bt[["team_name", "tasks_in_scope", "tasks_blocked", "blocked_pct", "tasks_reopened",
         "reopened_pct", "tasks_cancelled"]].sort_values("reopened_pct", ascending=False)
bl.columns = ["Team", "Tasks (excl. cancelled)", "Blocked", "Blocked %", "Reopened", "Reopened %", "Cancelled"]
st.dataframe(bl.style.background_gradient(subset=["Blocked %", "Reopened %"], cmap="Reds")
             .format({"Blocked %": "{:.1f}", "Reopened %": "{:.1f}"}), use_container_width=True, hide_index=True, height=620)
st.caption("Darker red = higher share. Blocked and reopened % use non-cancelled tasks as the base.")

mm = bs.melt(id_vars=["sprint_end_date", "sprint_name"], value_vars=["tasks_blocked", "tasks_reopened"],
             var_name="measure", value_name="tasks")
st.altair_chart(alt.Chart(mm).mark_line(point=True).encode(
    x=alt.X("sprint_end_date:T", title="Sprint end"),
    y=alt.Y("tasks:Q", title="Tasks"),
    color=alt.Color("measure:N", title="",
                    scale=alt.Scale(domain=["tasks_blocked", "tasks_reopened"],
                                    range=["#e15759", "#4f81bd"])),
    tooltip=["sprint_name", "measure", "tasks"]).properties(height=260),
    use_container_width=True)
# ---------------- findings ----------------
st.header("3 findings about team health")
bt_all = roll(dt, "team_name")
ov = roll(dt.assign(_all=1), "_all").iloc[0]
low = bt_all.loc[bt_all["on_time_pct"].idxmin()]
slow = bt_all.loc[bt_all["avg_cycle_days"].idxmax()]
rep = bt_all.loc[bt_all["reopened_pct"].idxmax()]
if ov.tasks_blocked > 0:
    blk = bt_all.loc[bt_all["blocked_pct"].idxmax()]
    blk_txt = (f"**{blk.team_name}** has the highest share of blocked work: {blk.blocked_pct:.1f}% of its tasks "
               f"({int(blk.tasks_blocked)} tasks) against {ov.blocked_pct:.1f}% overall.")
else:
    blk_txt = "No tasks carry a Blocked status in this data, so blocked work cannot be measured from it."
st.markdown(f"""
1. **Delivery reliability:** **{low.team_name}** has the lowest on-time rate at {low.on_time_pct:.1f}%, {ov.on_time_pct - low.on_time_pct:.1f} points below the overall {ov.on_time_pct:.1f}%.
2. **Slowest flow:** **{slow.team_name}** has the longest cycle time at {slow.avg_cycle_days:.1f} days against {ov.avg_cycle_days:.1f} days overall.
3. **Rework and blockers:** **{rep.team_name}** reopens the most work: {rep.reopened_pct:.1f}% of its tasks ({int(rep.tasks_reopened)}) against {ov.reopened_pct:.1f}% overall. {blk_txt}
""")
st.caption(f"Findings use all sprints for the selected teams. Cancelled tasks excluded: {int(ov.tasks_cancelled):,} "
           f"({100 * ov.tasks_cancelled / ov.tasks_total:.1f}% of all tasks).")