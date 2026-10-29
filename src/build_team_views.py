import duckdb
con = duckdb.connect("05_Starter/pulseiq.duckdb")

con.execute("""
CREATE OR REPLACE VIEW metrics.m29_team_sprint_delivery AS
SELECT *,
  ROUND(100.0 * done_on_time / NULLIF(tasks_done, 0), 1)       AS on_time_pct,
  ROUND(cycle_days_sum * 1.0 / NULLIF(cycle_task_count, 0), 1) AS avg_cycle_days
FROM (
  SELECT
    t.sprint_id, s.sprint_name, s.end_date AS sprint_end_date,
    t.team_id, COALESCE(tm.team_name, t.team_id) AS team_name,
    COUNT(*)                                                         AS tasks_total,
    COUNT(*) FILTER (WHERE UPPER(t.status) LIKE 'CANCEL%')           AS tasks_cancelled,
    COUNT(*) FILTER (WHERE UPPER(t.status) NOT LIKE 'CANCEL%')       AS tasks_in_scope,
    COUNT(*) FILTER (WHERE UPPER(t.status) = 'DONE')                 AS tasks_done,
    COALESCE(SUM(t.story_points) FILTER (WHERE UPPER(t.status) = 'DONE'), 0) AS velocity_points,
    COUNT(*) FILTER (WHERE UPPER(t.status) = 'DONE'
                     AND UPPER(t.completed_on_time) IN ('Y','YES','TRUE','1')) AS done_on_time,
    SUM(date_diff('day', t.started_date, t.completed_date))
        FILTER (WHERE UPPER(t.status) = 'DONE' AND t.started_date IS NOT NULL
                AND t.completed_date IS NOT NULL)                    AS cycle_days_sum,
    COUNT(*) FILTER (WHERE UPPER(t.status) = 'DONE' AND t.started_date IS NOT NULL
                AND t.completed_date IS NOT NULL)                    AS cycle_task_count,
    COUNT(*) FILTER (WHERE UPPER(t.status) LIKE 'BLOCK%')            AS tasks_blocked,
    COUNT(*) FILTER (WHERE t.reopened_count > 0)                     AS tasks_reopened
  FROM wh.fact_task t
  LEFT JOIN wh.dim_sprint s ON s.sprint_id = t.sprint_id
  LEFT JOIN wh.dim_team tm  ON tm.team_id  = t.team_id
  GROUP BY t.sprint_id, s.sprint_name, s.end_date, t.team_id, tm.team_name
)
""")
print("rows:", con.execute("SELECT COUNT(*) FROM metrics.m29_team_sprint_delivery").fetchall()[0][0])
print("teams:", con.execute("SELECT COUNT(DISTINCT team_id) FROM metrics.m29_team_sprint_delivery").fetchall()[0][0],
      "sprints:", con.execute("SELECT COUNT(DISTINCT sprint_id) FROM metrics.m29_team_sprint_delivery").fetchall()[0][0])