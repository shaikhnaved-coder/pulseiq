import duckdb, pandas as pd
pd.set_option("display.width", 220); pd.set_option("display.max_columns", None)
con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

# two teams to check: the one with most tasks and the one with fewest
tt = con.execute("""SELECT t.team_id, COALESCE(m.team_name, t.team_id) name, COUNT(*) n
                    FROM wh.fact_task t LEFT JOIN wh.dim_team m ON m.team_id = t.team_id
                    GROUP BY 1, 2 ORDER BY n DESC""").df()
picks = [tt.iloc[0], tt.iloc[-1]]

for p in picks:
    tid, name = p["team_id"], p["name"]
    raw = con.execute(f"""
        SELECT COUNT(*) tasks_total,
               COUNT(*) FILTER (WHERE UPPER(status) LIKE 'CANCEL%') cancelled,
               COUNT(*) FILTER (WHERE UPPER(status) = 'DONE') done,
               SUM(story_points) FILTER (WHERE UPPER(status) = 'DONE') velocity_points,
               ROUND(AVG(date_diff('day', started_date, completed_date))
                     FILTER (WHERE UPPER(status) = 'DONE'), 1) avg_cycle_days,
               ROUND(100.0 * COUNT(*) FILTER (WHERE UPPER(status) = 'DONE'
                     AND UPPER(completed_on_time) IN ('Y','YES','TRUE','1'))
                     / NULLIF(COUNT(*) FILTER (WHERE UPPER(status) = 'DONE'), 0), 1) on_time_pct,
               COUNT(*) FILTER (WHERE UPPER(status) LIKE 'BLOCK%') blocked,
               COUNT(*) FILTER (WHERE reopened_count > 0) reopened
        FROM wh.fact_task WHERE team_id = '{tid}'""").df()
    view = con.execute(f"""
        SELECT SUM(tasks_total) tasks_total, SUM(tasks_cancelled) cancelled, SUM(tasks_done) done,
               SUM(velocity_points) velocity_points,
               ROUND(SUM(cycle_days_sum) * 1.0 / SUM(cycle_task_count), 1) avg_cycle_days,
               ROUND(100.0 * SUM(done_on_time) / SUM(tasks_done), 1) on_time_pct,
               SUM(tasks_blocked) blocked, SUM(tasks_reopened) reopened
        FROM metrics.m29_team_sprint_delivery WHERE team_id = '{tid}'""").df()
    old = con.execute(f"""
        SELECT (SELECT SUM(velocity_points) FROM metrics.m24_velocity WHERE team_id = '{tid}') m24_velocity,
               (SELECT ROUND(AVG(avg_cycle_days), 1) FROM metrics.m25_avg_cycle_time WHERE team_id = '{tid}') m25_avg_of_sprints,
               (SELECT ROUND(AVG(on_time_pct), 1) FROM metrics.m23_on_time_delivery WHERE team_id = '{tid}') m23_avg_of_sprints""").df()
    print(f"\n===== TEAM: {name} ({tid}) =====")
    print("Raw task table :\n", raw.to_string(index=False))
    print("New page view  :\n", view.to_string(index=False))
    print("Earlier metrics (M23/M24/M25):\n", old.to_string(index=False))

    # CSV of one sprint's tasks to check by hand in Excel
    sp = con.execute(f"""SELECT sprint_id FROM wh.fact_task t JOIN wh.dim_sprint s USING (sprint_id)
                         WHERE t.team_id = '{tid}' ORDER BY s.end_date DESC LIMIT 1""").fetchall()[0][0]
    safe = "".join(ch for ch in name if ch.isalnum())
    out = f"docs/verify_{safe}_{sp}.csv"
    con.execute(f"""COPY (SELECT task_id, status, story_points, started_date, due_date, completed_date,
                          completed_on_time, reopened_count
                          FROM wh.fact_task WHERE team_id = '{tid}' AND sprint_id = '{sp}' ORDER BY task_id)
                    TO '{out}' (HEADER, DELIMITER ',')""")
    print("Saved tasks of the latest sprint for hand-checking:", out)