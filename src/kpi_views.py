import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb")

con.execute("""
CREATE OR REPLACE VIEW metrics.v_kpi_variance AS
WITH task_month AS (
    SELECT CAST(date_trunc('month', sprint_end_date) AS DATE) AS month_start_date,
           department_id,
           SUM(task_completion_pct * group_size) / SUM(group_size) AS task_completion_pct
    FROM metrics.m22_task_completion_rate
    GROUP BY 1, 2
),
actuals AS (
    SELECT month_start_date, department_id, 'Attendance rate' AS kpi, attendance_rate AS actual
    FROM metrics.m13_attendance_rate
    UNION ALL
    SELECT month_start_date, department_id, 'Overtime share %', overtime_share_pct
    FROM metrics.m11_overtime_share
    UNION ALL
    SELECT month_start_date, department_id, 'Monthly attrition %', attrition_pct
    FROM metrics.m04_attrition_monthly
    UNION ALL
    SELECT month_start_date, department_id, 'Task completion %', task_completion_pct
    FROM task_month
),
targets AS (
    SELECT CAST(month AS DATE) AS month_start_date, department_id,
           'Attendance rate' AS kpi, attendance_rate_target AS target, 'higher' AS direction
    FROM clean.kpi_targets
    UNION ALL
    SELECT CAST(month AS DATE), department_id,
           'Overtime share %', overtime_share_target_pct, 'lower'
    FROM clean.kpi_targets
    UNION ALL
    SELECT CAST(month AS DATE), department_id,
           'Monthly attrition %', attrition_monthly_target_pct, 'lower'
    FROM clean.kpi_targets
    UNION ALL
    SELECT CAST(month AS DATE), department_id,
           'Task completion %', task_completion_target_pct, 'higher'
    FROM clean.kpi_targets
),
joined AS (
    SELECT t.month_start_date, t.department_id, t.kpi, t.direction,
           t.target, a.actual,
           a.actual - t.target AS variance,
           ROUND((a.actual - t.target) * 100.0 / t.target, 2) AS variance_pct
    FROM targets t
    LEFT JOIN actuals a
           ON a.month_start_date = t.month_start_date
          AND a.department_id = t.department_id
          AND a.kpi = t.kpi
)
SELECT j.*, d.department_name,
       CASE
         WHEN j.actual IS NULL OR j.target IS NULL THEN 'Grey'
         WHEN j.direction = 'higher' AND j.actual >= j.target THEN 'Green'
         WHEN j.direction = 'lower'  AND j.actual <= j.target THEN 'Green'
         WHEN j.kpi = 'Attendance rate' AND j.target - j.actual <= 0.02 THEN 'Amber'
         WHEN j.kpi = 'Attendance rate' THEN 'Red'
         WHEN ABS(j.actual - j.target) <= 0.10 * j.target THEN 'Amber'
         ELSE 'Red'
       END AS status
FROM joined j
LEFT JOIN clean.dim_department d ON d.department_id = j.department_id
""")

v = "metrics.v_kpi_variance"

print("Rows in view (expect 720):", con.execute(f"SELECT COUNT(*) FROM {v}").fetchone()[0])

print()
print("Status counts by KPI:")
print(con.execute(f"""
    SELECT kpi, status, COUNT(*) AS n
    FROM {v} GROUP BY kpi, status ORDER BY kpi, status
""").df().to_string())

print()
print("Sample: first month, D04 and D10:")
print(con.execute(f"""
    SELECT month_start_date, department_id, kpi, target, actual, variance, variance_pct, status
    FROM {v}
    WHERE month_start_date = (SELECT MIN(month_start_date) FROM {v})
      AND department_id IN ('D04', 'D10')
    ORDER BY department_id, kpi
""").df().to_string())

print()
print("Sprints per department-month (roll-up check):")
print(con.execute("""
    SELECT MIN(n) AS min_sprints, MAX(n) AS max_sprints, COUNT(*) AS dept_months
    FROM (
        SELECT department_id,
               CAST(date_trunc('month', sprint_end_date) AS DATE) AS m,
               COUNT(DISTINCT sprint_id) AS n
        FROM metrics.m22_task_completion_rate
        GROUP BY 1, 2
    )
""").df().to_string())

print()
print("Attrition Grey rows (no actual):")
print(con.execute(f"""
    SELECT department_id, COUNT(*) AS n_months,
           MIN(month_start_date) AS first_m, MAX(month_start_date) AS last_m
    FROM {v} WHERE kpi = 'Monthly attrition %' AND status = 'Grey'
    GROUP BY department_id ORDER BY department_id
""").df().to_string())

print()
print("Attendance status counts after the change:")
print(con.execute(f"""
    SELECT status, COUNT(*) AS n FROM {v}
    WHERE kpi = 'Attendance rate' GROUP BY status ORDER BY status
""").df().to_string())