import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

checks = [
    ("m13_attendance_rate",  "attendance_rate"),
    ("m11_overtime_share",   "overtime_share_pct"),
    ("m04_attrition_monthly","attrition_pct"),
]

for view, col in checks:
    print("=" * 10, view, "=" * 10)
    print(con.execute(f"""
        SELECT MIN({col}) AS min_val,
               ROUND(AVG({col}), 4) AS avg_val,
               MAX({col}) AS max_val,
               COUNT(*) AS n_rows,
               COUNT(DISTINCT department_id) AS n_depts,
               MIN(month_start_date) AS first_month,
               MAX(month_start_date) AS last_month
        FROM metrics.{view}
    """).df().to_string())
    print(con.execute(f"""
        SELECT * FROM metrics.{view}
        ORDER BY month_start_date, department_id
        LIMIT 4
    """).df().to_string())
    print()

print("=" * 10, "m22_task_completion_rate", "=" * 10)
print(con.execute("""
    SELECT MIN(task_completion_pct) AS min_val,
           ROUND(AVG(task_completion_pct), 4) AS avg_val,
           MAX(task_completion_pct) AS max_val,
           COUNT(*) AS n_rows,
           COUNT(DISTINCT department_id) AS n_depts,
           COUNT(DISTINCT team_id) AS n_teams,
           MIN(sprint_end_date) AS first_sprint,
           MAX(sprint_end_date) AS last_sprint
    FROM metrics.m22_task_completion_rate
""").df().to_string())
print(con.execute("""
    SELECT * FROM metrics.m22_task_completion_rate
    ORDER BY sprint_end_date, department_id, team_id
    LIMIT 6
""").df().to_string())
print()
print("Departments present in m22:")
print(con.execute("""
    SELECT department_id, COUNT(*) AS n_rows
    FROM metrics.m22_task_completion_rate
    GROUP BY department_id ORDER BY department_id
""").df().to_string())