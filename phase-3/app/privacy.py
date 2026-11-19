import pandas as pd
from kpi_policy import METRICS, DIMENSIONS

MSG_SMALL = ("🔒 This selection covers too few people, so it is hidden to protect privacy. "
             "Remove a filter or go up one level.")

def build_where(scope, filters):
    clauses, params = ["1=1"], []
    for key, val in {**scope, **filters}.items():
        if val:
            clauses.append(f"p.{DIMENSIONS[key]} = ?")     # whitelisted column, value as parameter
            params.append(val)
    return " AND ".join(clauses), params

def explore(con, metric, dim, scope, filters, month_end):
    """Returns (visible_df, hidden_count, message). Small numbers never leave this function."""
    m = METRICS[metric]
    minimum = m["min_group"]
    where, wparams = build_where(scope, filters)
    me = pd.Timestamp(month_end)
    ctx = {"month_end": me.date(), "month_start": me.replace(day=1).date()}
    mparams = [ctx[k] for k in m["params"]]

    sql = f"""
        SELECT p.{DIMENSIONS[dim]} AS grp,
               COUNT(DISTINCT p.employee_id) AS n,
               {m['agg']} AS value
        FROM metrics.v_kpi_people p
        {m['join']}
        WHERE {where}
        GROUP BY 1
    """
    df = con.execute(sql, mparams + wparams).df()

    # Check 1: the whole filtered population must be big enough
    if df.empty or df["n"].sum() < minimum:
        return None, 0, MSG_SMALL

    # Check 2: every group must be big enough
    hide = df["n"] < minimum

    # Check 3: complementary suppression. If the hidden groups together are still
    # smaller than the minimum, someone could work them out by subtracting from a
    # total, so keep hiding the next-smallest visible group until the hidden pool is safe.
    while hide.any() and df.loc[hide, "n"].sum() < minimum and (~hide).any():
        hide.loc[df.loc[~hide, "n"].idxmin()] = True

    hidden = int(hide.sum())
    visible = (df.loc[~hide, ["grp", "n", "value"]]
                 .sort_values("value", ascending=False).reset_index(drop=True))
    if visible.empty:
        return None, hidden, ("🔒 Every group in this breakdown is too small to show on its own, "
                              "so all of them are hidden to protect privacy. "
                              "Try a different breakdown or a wider scope.")
    msg = ""
    if hidden:
        msg = (f"🔒 {hidden} group(s) hidden: fewer than {minimum} people, or hidden together "
               "with them so they cannot be worked out by subtraction.")
    return visible, hidden, msg

def visible_groups(con, dim, scope, minimum=5):
    """Names (never counts) of groups with at least `minimum` people.
    Used only to fill drill-down dropdowns. Tiny groups and the
    'No team assigned' bucket are left out."""
    where, params = build_where(scope, {})
    df = con.execute(f"""
        SELECT p.{DIMENSIONS[dim]} AS grp, COUNT(DISTINCT p.employee_id) AS n
        FROM metrics.v_kpi_people p
        WHERE {where}
        GROUP BY 1
    """, params).df()
    df = df[(df["n"] >= minimum) & (df["grp"] != "No team assigned")]
    return sorted(df["grp"].tolist())