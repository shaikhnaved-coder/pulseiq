import duckdb

con = duckdb.connect("phase-3/05_Starter/pulseiq.duckdb")   # write mode
con.execute("CREATE SCHEMA IF NOT EXISTS metrics")

# One row per ACTIVE person (current row only), Executive Office excluded (1 person).
# Team comes from fact_task: every tasked person is in exactly one team.
con.execute("""
CREATE OR REPLACE VIEW metrics.v_kpi_people AS
WITH team_map AS (
    SELECT assignee_employee_id AS employee_id, MIN(team_id) AS team_id
    FROM wh.fact_task
    GROUP BY 1
)
SELECT e.employee_id,
       d.department_name                         AS department,
       COALESCE(t.team_name, 'No team assigned') AS team,
       COALESCE(e.gender, 'Unknown')             AS gender,
       COALESCE(e.work_mode, 'Unknown')          AS work_mode,
       COALESCE(l.city_tier, 'Unknown')          AS city_tier
FROM wh.dim_employee e
JOIN wh.dim_department d ON d.department_id = e.department_id
LEFT JOIN team_map m     ON m.employee_id = e.employee_id
LEFT JOIN wh.dim_team t  ON t.team_id = m.team_id
LEFT JOIN wh.dim_location l ON l.work_location = e.work_location
WHERE e.is_current = 'Y'
  AND e.employment_status = 'Active'
  AND d.department_id <> 'D00'
""")

print(con.execute("""SELECT COUNT(*) AS rows, COUNT(DISTINCT employee_id) AS people
                     FROM metrics.v_kpi_people""").df())
print("(expect rows = people = 440, which is 441 active minus the Executive Office)")
print(con.execute("""SELECT department, team, COUNT(*) AS n
                     FROM metrics.v_kpi_people GROUP BY 1,2 ORDER BY n LIMIT 12""").df())
print(con.execute("""SELECT team, COUNT(*) AS n FROM metrics.v_kpi_people
                     WHERE team = 'Design Systems' GROUP BY 1""").df())
con.close()