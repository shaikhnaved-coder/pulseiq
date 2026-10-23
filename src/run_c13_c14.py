import duckdb
from datetime import datetime

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

# ---- C13: pipeline freshness (limit 24 hours) ----
last = con.execute(
    "SELECT MAX(CAST(run_at AS TIMESTAMP)) FROM etl.summary"
).fetchone()[0]
hours_old = (datetime.now() - last).total_seconds() / 3600
status = "PASS" if hours_old <= 24 else "FAIL"
print(f"DQ-C13 Pipeline freshness: last load {last}, "
      f"{hours_old:.1f} hours old -> {status}")

# ---- C14: groups smaller than the minimum ----
checks = {
"C14a Dept x month, fewer than 5 people (payroll)": """
    SELECT department_id,
           strftime(CAST(period_end_date AS DATE), '%Y-%m') AS month,
           COUNT(DISTINCT employee_id) AS people
    FROM wh.fact_payroll
    GROUP BY 1, 2
    HAVING COUNT(DISTINCT employee_id) < 5
""",
"C14b Dept x month, fewer than 10 people (attrition metrics)": """
    SELECT department_id,
           strftime(CAST(period_end_date AS DATE), '%Y-%m') AS month,
           COUNT(DISTINCT employee_id) AS people
    FROM wh.fact_payroll
    GROUP BY 1, 2
    HAVING COUNT(DISTINCT employee_id) < 10
""",
"C14c Team x sprint, fewer than 5 tasks": """
    SELECT team_id, sprint_id, COUNT(*) AS tasks
    FROM wh.fact_task
    GROUP BY 1, 2
    HAVING COUNT(*) < 5
""",
}

print()
for name, sql in checks.items():
    n = con.execute(f"SELECT COUNT(*) FROM ({sql})").fetchone()[0]
    print(f"{name:62} small groups: {n}")