import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # lets us import kpi_policy / privacy

import duckdb, pandas as pd, streamlit as st
from kpi_policy import METRICS, DIMENSIONS, ROLE_RULES, access_error
from privacy import explore, MSG_SMALL, visible_groups

def find_file(*parts):
    for p in Path(__file__).resolve().parents:
        c = p.joinpath(*parts)
        if c.exists():
            return str(c)
    raise FileNotFoundError("/".join(parts))

@st.cache_resource
def get_con():
    return duckdb.connect(find_file("05_Starter", "pulseiq.duckdb"), read_only=True)

con = get_con()
st.title("KPI Explorer")

# ---- 1. Demo user and role (demo login only, not real security) ----
users = pd.read_csv(find_file("05_Starter", "demo_users.csv"))
user = st.sidebar.selectbox("Demo user", users["username"])
role = str(users.loc[users["username"] == user, "role"].iloc[0]).upper()
rules = ROLE_RULES[role]
st.sidebar.write(f"Role: **{role}**")

# ---- 2. Month, metric, breakdown (only what this role may use) ----
months = con.execute("SELECT DISTINCT period_end_date FROM wh.fact_payroll ORDER BY 1 DESC").df().iloc[:, 0].tolist()
month_end = st.selectbox("Month", months, key=f"m_{role}",
                         format_func=lambda d: pd.Timestamp(d).strftime("%b %Y"))
metric = st.selectbox("Metric", rules["metrics"], key=f"metric_{role}",
                      format_func=lambda k: METRICS[k]["label"])
dim = st.selectbox("Break down by", rules["dims"], key=f"dim_{role}",
                   format_func=lambda k: k.replace("_", " ").title())

# ---- 3. Drill-down: Company -> Department -> Team ----
levels = rules["levels"]
level = st.radio("Level", levels, horizontal=True, key=f"lvl_{role}") if len(levels) > 1 else levels[0]
scope = {}

if rules.get("forced_scope"):
    scope = dict(rules["forced_scope"])
    st.info(f"Your scope: team **{scope['team']}** ({scope['department']})")
else:
    if level in ("Department", "Team"):
        d_opts = visible_groups(con, "department", {})
        if not d_opts:
            st.warning(MSG_SMALL)
            st.stop()
        scope["department"] = st.selectbox("Department", d_opts, key=f"dept_{role}")
    if level == "Team":
        t_opts = visible_groups(con, "team", {"department": scope["department"]})
        if not t_opts:
            st.info("No team in this department has enough people to show, "
                    "so team-level data is hidden here.")
            st.stop()
        scope["team"] = st.selectbox("Team", t_opts, key=f"team_{role}")

# ---- 4. Extra filters ----
filters = {}
with st.expander("Extra filters"):
    for fdim in [d for d in rules["dims"] if d not in ("department", "team")]:
        vals = con.execute(f"SELECT DISTINCT {DIMENSIONS[fdim]} FROM metrics.v_kpi_people ORDER BY 1").df().iloc[:, 0].tolist()
        pick = st.selectbox(f"Filter: {fdim.replace('_', ' ')}", ["(all)"] + vals, key=f"f_{role}_{fdim}")
        if pick != "(all)":
            filters[fdim] = pick

# ---- 5. Role check, then the gatekeeper ----
err = access_error(role, metric, dim, level, scope)
if err:
    st.error(err); st.stop()

vis, hidden, msg = explore(con, metric, dim, scope, filters, month_end)
if vis is None:
    st.warning(msg); st.stop()
if msg:
    st.warning(msg)

st.bar_chart(vis.set_index("grp")["value"])
shown = vis.copy()
shown["value"] = shown["value"].map(lambda v: METRICS[metric]["fmt"].format(v))
if metric == "headcount":
    shown = shown.drop(columns=["value"])      # "People" already is the headcount
    st.table(shown.rename(columns={"grp": dim.replace("_", " ").title(), "n": "People"}))
else:
    st.table(shown.rename(columns={"grp": dim.replace("_", " ").title(), "n": "People",
                                   "value": METRICS[metric]["label"]}))
st.caption("Population: employees active today, excluding the Executive Office (one person). "
           "Groups below the minimum group size (5 people) are never shown. Headcount does not change with the month.")
